//! Runtime-mutable configuration that can be updated remotely via heartbeat.
//!
//! Fields in [`DynamicConfig`] are initially populated from the static
//! [`Config`](crate::config::Config) and may be overridden by the Aether
//! management backend through the heartbeat response.

use std::collections::HashSet;
use std::sync::{Arc, OnceLock, RwLock};

use tracing::info;

use crate::config::Config;

/// Configuration that can be changed at runtime without restart.
#[derive(Debug)]
pub struct DynamicConfig {
    pub node_name: String,
    pub allowed_ports: HashSet<u16>,
    pub timestamp_tolerance: u64,
    pub log_level: String,
    pub heartbeat_interval: u64,
    /// Monotonically increasing version from the backend.
    /// `0` means no remote config has ever been applied.
    pub config_version: u64,
}

impl DynamicConfig {
    /// Initialize from static config (startup defaults).
    pub fn from_config(config: &Config) -> Self {
        Self {
            node_name: config.node_name.clone(),
            allowed_ports: config.allowed_ports.iter().copied().collect(),
            timestamp_tolerance: config.timestamp_tolerance,
            log_level: config.log_level.clone(),
            heartbeat_interval: config.heartbeat_interval,
            config_version: 0,
        }
    }
}

/// Shared dynamic config handle.
pub type SharedDynamicConfig = Arc<RwLock<DynamicConfig>>;

// ── Log-level hot-reload ─────────────────────────────────────────────────────

/// Global log-level reloader function, set during tracing init.
static LOG_RELOADER: OnceLock<Box<dyn Fn(&str) + Send + Sync>> = OnceLock::new();

/// Register the log-level reload function (called once from `init_tracing`).
pub fn set_log_reloader(f: Box<dyn Fn(&str) + Send + Sync>) {
    let _ = LOG_RELOADER.set(f);
}

/// Apply a remote config update to the dynamic config.
///
/// Returns `true` if the config was actually changed.
pub fn apply_remote_config(
    dynamic: &SharedDynamicConfig,
    remote: &crate::registration::client::RemoteConfig,
    version: u64,
) -> bool {
    let mut cfg = dynamic.write().unwrap();

    if version <= cfg.config_version {
        return false;
    }

    let mut changed = Vec::new();

    if let Some(ref name) = remote.node_name {
        if *name != cfg.node_name {
            changed.push(format!("node_name → {}", name));
            cfg.node_name = name.clone();
        }
    }

    if let Some(ref ports) = remote.allowed_ports {
        let new_set: HashSet<u16> = ports.iter().copied().collect();
        if new_set != cfg.allowed_ports {
            changed.push(format!("allowed_ports → {:?}", ports));
            cfg.allowed_ports = new_set;
        }
    }

    if let Some(tol) = remote.timestamp_tolerance {
        if tol != cfg.timestamp_tolerance {
            changed.push(format!("timestamp_tolerance → {}", tol));
            cfg.timestamp_tolerance = tol;
        }
    }

    if let Some(interval) = remote.heartbeat_interval {
        if interval != cfg.heartbeat_interval {
            changed.push(format!("heartbeat_interval → {}s", interval));
            cfg.heartbeat_interval = interval;
        }
    }

    if let Some(ref level) = remote.log_level {
        if *level != cfg.log_level {
            changed.push(format!("log_level → {}", level));
            cfg.log_level = level.clone();
            // Hot-reload tracing filter
            if let Some(reloader) = LOG_RELOADER.get() {
                reloader(level);
            }
        }
    }

    cfg.config_version = version;

    if !changed.is_empty() {
        info!(
            version,
            changes = %changed.join(", "),
            "remote config applied"
        );
    }

    !changed.is_empty()
}
