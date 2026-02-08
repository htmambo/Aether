use std::collections::HashSet;
use std::sync::Arc;

use hyper::body::Incoming;
use hyper::{Request, Response};
use tokio::net::TcpStream;
use tracing::{debug, warn};

use crate::auth;
use crate::config::Config;
use crate::proxy::target_filter;

/// Handle HTTP CONNECT tunnel requests.
///
/// Flow: validate auth -> check target filter -> TCP connect -> 200 -> bidirectional copy
pub async fn handle_connect(
    req: Request<Incoming>,
    config: Arc<Config>,
    node_id: &str,
    allowed_ports: &HashSet<u16>,
    timestamp_tolerance: u64,
) -> Response<http_body_util::Empty<bytes::Bytes>> {
    // Extract Proxy-Authorization header
    let proxy_auth = req
        .headers()
        .get("proxy-authorization")
        .and_then(|v| v.to_str().ok());

    // HMAC authentication
    if let Err(e) = auth::validate_proxy_auth(proxy_auth, &config, node_id, timestamp_tolerance) {
        warn!(error = %e, "CONNECT auth failed");
        return proxy_auth_required(&e.to_string());
    }

    // Parse target host:port from CONNECT URI
    let authority = match req.uri().authority() {
        Some(auth) => auth.clone(),
        None => {
            warn!("CONNECT request missing authority");
            return bad_request("missing target authority");
        }
    };

    let host = authority.host().to_string();
    let port = authority.port_u16().unwrap_or(443);

    // Target filter: private IP + port whitelist
    let target_addr = match target_filter::validate_target(&host, port, allowed_ports) {
        Ok(addr) => addr,
        Err(e) => {
            warn!(host = %host, port, error = %e, "CONNECT target rejected");
            return forbidden(&e.to_string());
        }
    };

    debug!(target = %target_addr, "CONNECT tunnel establishing");

    // Connect to target
    let target_stream = match TcpStream::connect(target_addr).await {
        Ok(s) => s,
        Err(e) => {
            warn!(target = %target_addr, error = %e, "CONNECT target connection failed");
            return bad_gateway(&e.to_string());
        }
    };

    // Respond 200 and upgrade connection to raw TCP tunnel
    let target_display = target_addr.to_string();
    tokio::task::spawn(async move {
        match hyper::upgrade::on(req).await {
            Ok(upgraded) => {
                let mut upgraded = hyper_util::rt::TokioIo::new(upgraded);
                let mut target = target_stream;

                match tokio::io::copy_bidirectional(&mut upgraded, &mut target).await {
                    Ok((from_client, from_target)) => {
                        debug!(
                            target = %target_display,
                            from_client,
                            from_target,
                            "CONNECT tunnel closed"
                        );
                    }
                    Err(e) => {
                        debug!(target = %target_display, error = %e, "CONNECT tunnel error");
                    }
                }
            }
            Err(e) => {
                warn!(target = %target_display, error = %e, "CONNECT upgrade failed");
            }
        }
    });

    Response::builder()
        .status(200)
        .body(http_body_util::Empty::new())
        .unwrap()
}

fn proxy_auth_required(msg: &str) -> Response<http_body_util::Empty<bytes::Bytes>> {
    Response::builder()
        .status(407)
        .header("Proxy-Authenticate", "HMAC-SHA256")
        .header("Content-Length", "0")
        .header("X-Error", msg)
        .body(http_body_util::Empty::new())
        .unwrap()
}

fn forbidden(msg: &str) -> Response<http_body_util::Empty<bytes::Bytes>> {
    Response::builder()
        .status(403)
        .header("Content-Length", "0")
        .header("X-Error", msg)
        .body(http_body_util::Empty::new())
        .unwrap()
}

fn bad_request(msg: &str) -> Response<http_body_util::Empty<bytes::Bytes>> {
    Response::builder()
        .status(400)
        .header("Content-Length", "0")
        .header("X-Error", msg)
        .body(http_body_util::Empty::new())
        .unwrap()
}

fn bad_gateway(msg: &str) -> Response<http_body_util::Empty<bytes::Bytes>> {
    Response::builder()
        .status(502)
        .header("Content-Length", "0")
        .header("X-Error", msg)
        .body(http_body_util::Empty::new())
        .unwrap()
}
