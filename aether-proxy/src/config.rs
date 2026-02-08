use std::path::Path;

use clap::Parser;
use serde::{Deserialize, Serialize};

/// Aether forward proxy with HMAC authentication.
///
/// Deployed on overseas VPS to relay API traffic for Aether instances
/// behind the GFW. Registers with Aether, sends heartbeats, and validates
/// incoming proxy requests via HMAC-SHA256 signatures in Basic Auth.
#[derive(Parser, Debug, Clone)]
#[command(version, about)]
pub struct Config {
    /// Aether server URL (e.g. https://aether.example.com)
    #[arg(long, env = "AETHER_PROXY_AETHER_URL")]
    pub aether_url: String,

    /// Management Token for Aether admin API (ae_xxx)
    #[arg(long, env = "AETHER_PROXY_MANAGEMENT_TOKEN")]
    pub management_token: String,

    /// HMAC-SHA256 key for proxy authentication
    #[arg(long, env = "AETHER_PROXY_HMAC_KEY")]
    pub hmac_key: String,

    /// Port to listen on for proxy connections
    #[arg(long, env = "AETHER_PROXY_LISTEN_PORT", default_value_t = 18080)]
    pub listen_port: u16,

    /// Public IP address of this node (auto-detected if omitted)
    #[arg(long, env = "AETHER_PROXY_PUBLIC_IP")]
    pub public_ip: Option<String>,

    /// Human-readable node name
    #[arg(long, env = "AETHER_PROXY_NODE_NAME", default_value = "proxy-01")]
    pub node_name: String,

    /// Region label (e.g. ap-northeast-1)
    #[arg(long, env = "AETHER_PROXY_NODE_REGION")]
    pub node_region: Option<String>,

    /// Heartbeat interval in seconds
    #[arg(long, env = "AETHER_PROXY_HEARTBEAT_INTERVAL", default_value_t = 30)]
    pub heartbeat_interval: u64,

    /// Allowed destination ports (default: 80,443,8080,8443)
    #[arg(long, env = "AETHER_PROXY_ALLOWED_PORTS", value_delimiter = ',', default_values_t = vec![80, 443, 8080, 8443])]
    pub allowed_ports: Vec<u16>,

    /// Timestamp tolerance window in seconds for HMAC validation
    #[arg(long, env = "AETHER_PROXY_TIMESTAMP_TOLERANCE", default_value_t = 300)]
    pub timestamp_tolerance: u64,

    /// Log level (trace, debug, info, warn, error)
    #[arg(long, env = "AETHER_PROXY_LOG_LEVEL", default_value = "info")]
    pub log_level: String,

    /// Output logs as JSON
    #[arg(long, env = "AETHER_PROXY_LOG_JSON", default_value_t = false)]
    pub log_json: bool,

    /// Enable TLS encryption (dual-stack: accepts both HTTP and TLS on same port)
    #[arg(long, env = "AETHER_PROXY_ENABLE_TLS", default_value_t = true)]
    pub enable_tls: bool,

    /// Path to TLS certificate PEM file
    #[arg(
        long,
        env = "AETHER_PROXY_TLS_CERT",
        default_value = "aether-proxy-cert.pem"
    )]
    pub tls_cert: String,

    /// Path to TLS private key PEM file
    #[arg(
        long,
        env = "AETHER_PROXY_TLS_KEY",
        default_value = "aether-proxy-key.pem"
    )]
    pub tls_key: String,
}

// ---------------------------------------------------------------------------
// TOML config file support
// ---------------------------------------------------------------------------

/// Serializable config for TOML file persistence.
/// All fields are optional — only populated values are written.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct ConfigFile {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub aether_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub management_token: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hmac_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub listen_port: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub public_ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node_region: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub heartbeat_interval: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub allowed_ports: Option<Vec<u16>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp_tolerance: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub log_level: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub log_json: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub enable_tls: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tls_cert: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tls_key: Option<String>,
}

impl ConfigFile {
    /// Load from a TOML file.
    pub fn load(path: &Path) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        Ok(toml::from_str(&content)?)
    }

    /// Save to a TOML file.
    pub fn save(&self, path: &Path) -> anyhow::Result<()> {
        let content = toml::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }

    /// Inject values as environment variables so clap picks them up.
    ///
    /// Only sets variables that are **not** already present in the
    /// environment, preserving the precedence: CLI > env > config file.
    pub fn inject_env(&self) {
        macro_rules! set {
            ($env:expr, $val:expr) => {
                if let Some(ref v) = $val {
                    if std::env::var($env).is_err() {
                        std::env::set_var($env, v.to_string());
                    }
                }
            };
        }
        set!("AETHER_PROXY_AETHER_URL", self.aether_url);
        set!("AETHER_PROXY_MANAGEMENT_TOKEN", self.management_token);
        set!("AETHER_PROXY_HMAC_KEY", self.hmac_key);
        set!("AETHER_PROXY_LISTEN_PORT", self.listen_port);
        set!("AETHER_PROXY_PUBLIC_IP", self.public_ip);
        set!("AETHER_PROXY_NODE_NAME", self.node_name);
        set!("AETHER_PROXY_NODE_REGION", self.node_region);
        set!("AETHER_PROXY_HEARTBEAT_INTERVAL", self.heartbeat_interval);
        set!("AETHER_PROXY_TIMESTAMP_TOLERANCE", self.timestamp_tolerance);
        set!("AETHER_PROXY_LOG_LEVEL", self.log_level);
        set!("AETHER_PROXY_LOG_JSON", self.log_json);
        set!("AETHER_PROXY_ENABLE_TLS", self.enable_tls);
        set!("AETHER_PROXY_TLS_CERT", self.tls_cert);
        set!("AETHER_PROXY_TLS_KEY", self.tls_key);

        // allowed_ports needs special handling (comma-separated)
        if let Some(ref ports) = self.allowed_ports {
            if std::env::var("AETHER_PROXY_ALLOWED_PORTS").is_err() {
                let s: String = ports
                    .iter()
                    .map(|p| p.to_string())
                    .collect::<Vec<_>>()
                    .join(",");
                std::env::set_var("AETHER_PROXY_ALLOWED_PORTS", s);
            }
        }
    }
}
