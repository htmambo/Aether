use base64::Engine;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use subtle::ConstantTimeEq;

use crate::config::Config;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug)]
pub enum AuthError {
    MissingHeader,
    InvalidBasicAuth,
    InvalidUsername,
    InvalidPasswordFormat,
    TimestampParseError,
    TimestampExpired,
    SignatureMismatch,
}

impl std::fmt::Display for AuthError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingHeader => write!(f, "missing Proxy-Authorization header"),
            Self::InvalidBasicAuth => write!(f, "invalid Basic auth encoding"),
            Self::InvalidUsername => write!(f, "username must be 'hmac'"),
            Self::InvalidPasswordFormat => {
                write!(f, "password format must be 'timestamp.signature'")
            }
            Self::TimestampParseError => write!(f, "invalid timestamp"),
            Self::TimestampExpired => write!(f, "timestamp outside tolerance window"),
            Self::SignatureMismatch => write!(f, "HMAC signature mismatch"),
        }
    }
}

/// Validate Proxy-Authorization header.
///
/// Expected format: `Basic base64(hmac:{timestamp}.{signature})`
/// where signature = hex(HMAC-SHA256(hmac_key, "{timestamp}\n{node_id}"))
///
/// `timestamp_tolerance` is accepted separately so the caller can supply
/// the value from [`DynamicConfig`](crate::runtime::DynamicConfig) (which
/// may be updated remotely).
pub fn validate_proxy_auth(
    proxy_auth_header: Option<&str>,
    config: &Config,
    node_id: &str,
    timestamp_tolerance: u64,
) -> Result<(), AuthError> {
    let header = proxy_auth_header.ok_or(AuthError::MissingHeader)?;

    let encoded = header
        .strip_prefix("Basic ")
        .or_else(|| header.strip_prefix("basic "))
        .ok_or(AuthError::InvalidBasicAuth)?;

    let decoded_bytes = base64::engine::general_purpose::STANDARD
        .decode(encoded.trim())
        .map_err(|_| AuthError::InvalidBasicAuth)?;

    let decoded = String::from_utf8(decoded_bytes).map_err(|_| AuthError::InvalidBasicAuth)?;

    // format: hmac:{timestamp}.{signature}
    let (username, password) = decoded.split_once(':').ok_or(AuthError::InvalidBasicAuth)?;

    if username != "hmac" {
        return Err(AuthError::InvalidUsername);
    }

    let (timestamp_str, signature_hex) = password
        .split_once('.')
        .ok_or(AuthError::InvalidPasswordFormat)?;

    // Validate timestamp window
    let timestamp: u64 = timestamp_str
        .parse()
        .map_err(|_| AuthError::TimestampParseError)?;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("system clock before epoch")
        .as_secs();

    let diff = now.abs_diff(timestamp);

    if diff > timestamp_tolerance {
        return Err(AuthError::TimestampExpired);
    }

    // Recompute signature
    let payload = format!("{}\n{}", timestamp_str, node_id);
    let mut mac =
        HmacSha256::new_from_slice(config.hmac_key.as_bytes()).expect("HMAC accepts any key size");
    mac.update(payload.as_bytes());
    let expected = mac.finalize().into_bytes();
    let expected_hex = hex::encode(expected);

    // Constant-time comparison
    let sig_bytes = signature_hex.as_bytes();
    let exp_bytes = expected_hex.as_bytes();

    if sig_bytes.len() != exp_bytes.len() || sig_bytes.ct_eq(exp_bytes).unwrap_u8() != 1 {
        return Err(AuthError::SignatureMismatch);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_config() -> Config {
        Config {
            aether_url: String::new(),
            management_token: String::new(),
            hmac_key: "test-hmac-key".to_string(),
            listen_port: 18080,
            public_ip: None,
            node_name: "test".to_string(),
            node_region: None,
            heartbeat_interval: 30,
            allowed_ports: vec![80, 443],
            timestamp_tolerance: 300,
            log_level: "info".to_string(),
            log_json: false,
            enable_tls: false,
            tls_cert: String::new(),
            tls_key: String::new(),
        }
    }

    fn make_valid_auth(config: &Config, node_id: &str) -> String {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        let payload = format!("{}\n{}", now, node_id);
        let mut mac = HmacSha256::new_from_slice(config.hmac_key.as_bytes()).unwrap();
        mac.update(payload.as_bytes());
        let sig = hex::encode(mac.finalize().into_bytes());
        let cred = format!("hmac:{}.{}", now, sig);
        let encoded = base64::engine::general_purpose::STANDARD.encode(cred);
        format!("Basic {}", encoded)
    }

    #[test]
    fn test_valid_auth() {
        let config = make_config();
        let header = make_valid_auth(&config, "node-1");
        assert!(
            validate_proxy_auth(Some(&header), &config, "node-1", config.timestamp_tolerance)
                .is_ok()
        );
    }

    #[test]
    fn test_wrong_node_id() {
        let config = make_config();
        let header = make_valid_auth(&config, "node-1");
        assert!(matches!(
            validate_proxy_auth(Some(&header), &config, "node-2", config.timestamp_tolerance),
            Err(AuthError::SignatureMismatch)
        ));
    }

    #[test]
    fn test_missing_header() {
        let config = make_config();
        assert!(matches!(
            validate_proxy_auth(None, &config, "node-1", config.timestamp_tolerance),
            Err(AuthError::MissingHeader)
        ));
    }

    #[test]
    fn test_wrong_username() {
        let cred = "user:12345.abc";
        let encoded = base64::engine::general_purpose::STANDARD.encode(cred);
        let header = format!("Basic {}", encoded);
        let config = make_config();
        assert!(matches!(
            validate_proxy_auth(Some(&header), &config, "node-1", config.timestamp_tolerance),
            Err(AuthError::InvalidUsername)
        ));
    }
}
