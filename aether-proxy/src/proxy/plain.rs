use std::collections::HashSet;
use std::sync::Arc;

use http_body_util::{BodyExt, Full};
use hyper::body::Incoming;
use hyper::{Request, Response};
use tracing::{debug, info, warn};

use crate::auth;
use crate::config::Config;
use crate::proxy::target_filter;

/// Boxed body that unifies `Full` (error responses) and `Incoming` (streamed upstream).
pub type BoxBody =
    http_body_util::combinators::BoxBody<bytes::Bytes, Box<dyn std::error::Error + Send + Sync>>;

/// Handle plain HTTP forward proxy requests (non-CONNECT).
///
/// Flow: validate auth -> check target filter -> forward request -> **stream** response
pub async fn handle_plain(
    req: Request<Incoming>,
    config: Arc<Config>,
    node_id: &str,
    allowed_ports: &HashSet<u16>,
    timestamp_tolerance: u64,
) -> Response<BoxBody> {
    // Extract Proxy-Authorization header
    let proxy_auth = req
        .headers()
        .get("proxy-authorization")
        .and_then(|v| v.to_str().ok());

    // HMAC authentication
    if let Err(e) = auth::validate_proxy_auth(proxy_auth, &config, node_id, timestamp_tolerance) {
        warn!(error = %e, "HTTP proxy auth failed");
        return proxy_auth_required(&e.to_string());
    }

    // Parse target from absolute URI
    let uri = req.uri().clone();
    let host = match uri.host() {
        Some(h) => h.to_string(),
        None => {
            warn!(uri = %uri, "HTTP proxy request missing host");
            return bad_request("missing host in URI");
        }
    };
    let port = uri.port_u16().unwrap_or(80);

    // Target filter
    let target_addr = match target_filter::validate_target(&host, port, allowed_ports) {
        Ok(addr) => addr,
        Err(e) => {
            warn!(host = %host, port, error = %e, "HTTP proxy target rejected");
            return forbidden(&e.to_string());
        }
    };

    info!(target = %target_addr, method = %req.method(), "HTTP proxy forwarding");

    // Build outgoing request (strip proxy headers, use relative URI)
    let path_and_query = uri
        .path_and_query()
        .map(|pq| pq.as_str())
        .unwrap_or("/");

    let mut builder = Request::builder()
        .method(req.method())
        .uri(path_and_query)
        .version(req.version());

    // Copy headers, skipping proxy-specific ones
    for (name, value) in req.headers() {
        if name == "proxy-authorization" || name == "proxy-connection" {
            continue;
        }
        builder = builder.header(name, value);
    }

    // Collect the incoming request body (client payloads are small)
    let body_bytes = match req.into_body().collect().await {
        Ok(collected) => collected.to_bytes(),
        Err(e) => {
            warn!(error = %e, "failed to read request body");
            return bad_gateway("failed to read request body");
        }
    };

    // Connect and send via raw TCP + hyper client
    let stream = match tokio::net::TcpStream::connect(target_addr).await {
        Ok(s) => s,
        Err(e) => {
            warn!(target = %target_addr, error = %e, "HTTP proxy connection failed");
            return bad_gateway(&format!("connection failed: {}", e));
        }
    };

    let io = hyper_util::rt::TokioIo::new(stream);
    let (mut sender, conn) = match hyper::client::conn::http1::handshake(io).await {
        Ok(pair) => pair,
        Err(e) => {
            warn!(error = %e, "HTTP handshake failed");
            return bad_gateway(&format!("handshake failed: {}", e));
        }
    };

    tokio::task::spawn(async move {
        if let Err(e) = conn.await {
            debug!(error = %e, "HTTP proxy client connection error");
        }
    });

    let outgoing = builder
        .body(Full::new(body_bytes))
        .expect("failed to build outgoing request");

    match sender.send_request(outgoing).await {
        Ok(resp) => {
            info!(target = %target_addr, status = resp.status().as_u16(), "HTTP proxy response");
            // Stream the response body directly — no buffering
            let (parts, body) = resp.into_parts();
            let body: BoxBody = body
                .map_err(|e| -> Box<dyn std::error::Error + Send + Sync> { Box::new(e) })
                .boxed();
            Response::from_parts(parts, body)
        }
        Err(e) => {
            warn!(error = %e, "HTTP proxy request failed");
            bad_gateway(&format!("upstream request failed: {}", e))
        }
    }
}

// ── Error response helpers ───────────────────────────────────────────────────

fn empty_box() -> BoxBody {
    Full::new(bytes::Bytes::new())
        .map_err(|e| -> Box<dyn std::error::Error + Send + Sync> { match e {} })
        .boxed()
}

fn proxy_auth_required(msg: &str) -> Response<BoxBody> {
    Response::builder()
        .status(407)
        .header("Proxy-Authenticate", "HMAC-SHA256")
        .header("X-Error", msg)
        .body(empty_box())
        .unwrap()
}

fn forbidden(msg: &str) -> Response<BoxBody> {
    Response::builder()
        .status(403)
        .header("X-Error", msg)
        .body(empty_box())
        .unwrap()
}

fn bad_request(msg: &str) -> Response<BoxBody> {
    Response::builder()
        .status(400)
        .header("X-Error", msg)
        .body(empty_box())
        .unwrap()
}

fn bad_gateway(msg: &str) -> Response<BoxBody> {
    Response::builder()
        .status(502)
        .header("X-Error", msg)
        .body(empty_box())
        .unwrap()
}
