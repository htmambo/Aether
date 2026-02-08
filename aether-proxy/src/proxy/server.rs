use std::net::SocketAddr;
use std::sync::atomic::Ordering;
use std::sync::Arc;

use http_body_util::BodyExt;
use hyper::body::Incoming;
use hyper::rt::{Read, Write};
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Method, Request};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;
use tokio::sync::watch;
use tracing::{debug, info, warn};

use crate::proxy::{connect, delegate, plain, tls};
use crate::state::AppState;

/// Start the proxy server.
///
/// Listens for incoming TCP connections and dispatches:
/// - CONNECT requests -> tunnel handler
/// - Other HTTP requests -> plain forward proxy handler
///
/// When TLS is configured, the server operates in dual-stack mode:
/// it peeks at the first byte of each connection to distinguish TLS ClientHello
/// (0x16) from plain HTTP, and handles both on the same port.
pub async fn run(
    state: &Arc<AppState>,
    mut shutdown_rx: watch::Receiver<bool>,
) -> anyhow::Result<()> {
    let addr = SocketAddr::from(([0, 0, 0, 0], state.config.listen_port));
    let listener = TcpListener::bind(addr).await?;

    if state.tls_acceptor.is_some() {
        info!(addr = %addr, "proxy server listening (HTTP+TLS dual-stack)");
    } else {
        info!(addr = %addr, "proxy server listening (HTTP only)");
    }

    loop {
        tokio::select! {
            result = listener.accept() => {
                let (stream, peer_addr) = match result {
                    Ok(v) => v,
                    Err(e) => {
                        warn!(error = %e, "failed to accept connection");
                        continue;
                    }
                };

                debug!(peer = %peer_addr, "new connection");

                let state = Arc::clone(state);
                state.active_connections.fetch_add(1, Ordering::Relaxed);

                tokio::task::spawn(async move {
                    // Dual-stack: peek first byte to decide TLS vs plain HTTP
                    if let Some(ref acceptor) = state.tls_acceptor {
                        if tls::is_tls_client_hello(&stream).await {
                            match acceptor.clone().accept(stream).await {
                                Ok(tls_stream) => {
                                    debug!(peer = %peer_addr, "TLS handshake ok");
                                    serve_connection(
                                        TokioIo::new(tls_stream),
                                        peer_addr,
                                        &state,
                                    )
                                    .await;
                                }
                                Err(e) => {
                                    debug!(peer = %peer_addr, error = %e, "TLS handshake failed");
                                }
                            }
                            state.active_connections.fetch_sub(1, Ordering::Relaxed);
                            return;
                        }
                    }

                    // Plain HTTP
                    serve_connection(
                        TokioIo::new(stream),
                        peer_addr,
                        &state,
                    )
                    .await;

                    state.active_connections.fetch_sub(1, Ordering::Relaxed);
                });
            }
            _ = shutdown_rx.changed() => {
                info!("proxy server shutting down");
                break;
            }
        }
    }

    Ok(())
}

/// Serve a single HTTP/1.1 connection (works over both plain TCP and TLS).
async fn serve_connection<I>(io: I, peer_addr: SocketAddr, state: &Arc<AppState>)
where
    I: Read + Write + Unpin + Send + 'static,
{
    let config = Arc::clone(&state.config);
    let node_id = Arc::clone(&state.node_id);
    let dynamic = Arc::clone(&state.dynamic);
    let delegate_client = state.delegate_client.clone();

    let service = service_fn(move |req: Request<Incoming>| {
        let config = Arc::clone(&config);
        let node_id = Arc::clone(&node_id);
        let dynamic = Arc::clone(&dynamic);
        let delegate_client = delegate_client.clone();

        async move {
            type BoxBody = http_body_util::combinators::BoxBody<
                bytes::Bytes,
                Box<dyn std::error::Error + Send + Sync>,
            >;

            // Snapshot current dynamic values (may be updated by remote config)
            let current_node_id = node_id.read().unwrap().clone();
            let (allowed_ports, timestamp_tolerance) = {
                let d = dynamic.read().unwrap();
                (d.allowed_ports.clone(), d.timestamp_tolerance)
            };

            if req.method() == Method::CONNECT {
                let resp = connect::handle_connect(
                    req,
                    config,
                    &current_node_id,
                    &allowed_ports,
                    timestamp_tolerance,
                )
                .await;
                let resp = resp.map(|_| -> BoxBody {
                    http_body_util::Empty::new()
                        .map_err(|e| -> Box<dyn std::error::Error + Send + Sync> { match e {} })
                        .boxed()
                });
                Ok::<_, hyper::Error>(resp)
            } else if req.uri().path() == "/_aether/delegate" && req.method() == hyper::Method::POST
            {
                let resp = delegate::handle_delegate(
                    req,
                    config,
                    &current_node_id,
                    &allowed_ports,
                    timestamp_tolerance,
                    &delegate_client,
                )
                .await;
                Ok(resp)
            } else {
                let resp = plain::handle_plain(
                    req,
                    config,
                    &current_node_id,
                    &allowed_ports,
                    timestamp_tolerance,
                )
                .await;
                Ok(resp)
            }
        }
    });

    if let Err(e) = http1::Builder::new()
        .preserve_header_case(true)
        .title_case_headers(false)
        .serve_connection(io, service)
        .with_upgrades()
        .await
    {
        if !e.to_string().contains("connection closed") {
            debug!(peer = %peer_addr, error = %e, "connection error");
        }
    }
}
