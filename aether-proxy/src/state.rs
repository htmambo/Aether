//! Shared application state passed to all subsystems.
//!
//! Consolidates the multiple `Arc<...>` parameters that were previously
//! threaded individually through proxy server, heartbeat, and handlers.

use std::sync::atomic::AtomicU64;
use std::sync::{Arc, RwLock};

use tokio_rustls::TlsAcceptor;

use crate::config::Config;
use crate::hardware::HardwareInfo;
use crate::registration::client::AetherClient;
use crate::runtime::SharedDynamicConfig;

/// Central application state shared across all tasks.
pub struct AppState {
    pub config: Arc<Config>,
    pub node_id: Arc<RwLock<String>>,
    pub dynamic: SharedDynamicConfig,
    pub aether_client: Arc<AetherClient>,
    pub hardware_info: Arc<HardwareInfo>,
    pub public_ip: String,
    pub tls_fingerprint: Option<String>,
    pub tls_acceptor: Option<TlsAcceptor>,
    /// Shared reqwest client for delegate mode (proxy issues upstream requests directly).
    pub delegate_client: reqwest::Client,
    /// Active connection count for metrics reporting.
    pub active_connections: Arc<AtomicU64>,
}
