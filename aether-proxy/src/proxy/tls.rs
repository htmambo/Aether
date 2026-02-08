use std::fs;
use std::io::BufReader;
use std::path::Path;
use std::sync::Arc;

use rcgen::{CertificateParams, KeyPair};
use rustls_pki_types::{CertificateDer, PrivateKeyDer};
use sha2::{Digest, Sha256};
use tokio_rustls::TlsAcceptor;
use tracing::{info, warn};

/// Generate a self-signed certificate if the files do not already exist.
///
/// The certificate includes SANs: `localhost` and `aether-proxy`.
/// The private key file is set to mode 0600 on unix.
pub fn ensure_self_signed_cert(cert_path: &Path, key_path: &Path) -> anyhow::Result<()> {
    if cert_path.exists() && key_path.exists() {
        info!(
            cert = %cert_path.display(),
            key = %key_path.display(),
            "using existing TLS certificate"
        );
        return Ok(());
    }

    info!("generating self-signed TLS certificate");

    let mut params = CertificateParams::new(vec!["localhost".into(), "aether-proxy".into()])?;
    params.distinguished_name = rcgen::DistinguishedName::new();
    params
        .distinguished_name
        .push(rcgen::DnType::CommonName, "aether-proxy");

    let key_pair = KeyPair::generate()?;
    let cert = params.self_signed(&key_pair)?;

    let cert_pem = cert.pem();
    let key_pem = key_pair.serialize_pem();

    fs::write(cert_path, &cert_pem)?;
    fs::write(key_path, &key_pem)?;

    // Set key file permissions to 0600 on unix
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let perms = fs::Permissions::from_mode(0o600);
        fs::set_permissions(key_path, perms)?;
    }

    info!(
        cert = %cert_path.display(),
        key = %key_path.display(),
        "self-signed TLS certificate generated"
    );

    Ok(())
}

/// Build a `TlsAcceptor` from PEM certificate and key files.
pub fn build_tls_acceptor(cert_path: &Path, key_path: &Path) -> anyhow::Result<TlsAcceptor> {
    let cert_file = fs::File::open(cert_path)?;
    let key_file = fs::File::open(key_path)?;

    let certs: Vec<CertificateDer<'static>> =
        rustls_pemfile::certs(&mut BufReader::new(cert_file)).collect::<Result<Vec<_>, _>>()?;

    if certs.is_empty() {
        anyhow::bail!("no certificates found in {}", cert_path.display());
    }

    let key: PrivateKeyDer<'static> =
        rustls_pemfile::private_key(&mut BufReader::new(key_file))?
            .ok_or_else(|| anyhow::anyhow!("no private key found in {}", key_path.display()))?;

    let config = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)?;

    Ok(TlsAcceptor::from(Arc::new(config)))
}

/// Compute the SHA-256 fingerprint of the first certificate in a PEM file.
///
/// Returns the hex-encoded fingerprint (lowercase, no separators).
pub fn cert_sha256_fingerprint(cert_path: &Path) -> anyhow::Result<String> {
    let cert_file = fs::File::open(cert_path)?;
    let certs: Vec<CertificateDer<'static>> =
        rustls_pemfile::certs(&mut BufReader::new(cert_file)).collect::<Result<Vec<_>, _>>()?;

    let cert = certs
        .first()
        .ok_or_else(|| anyhow::anyhow!("no certificates found in {}", cert_path.display()))?;

    let digest = Sha256::digest(cert.as_ref());
    Ok(hex::encode(digest))
}

/// Peek at the first byte of a TCP stream to determine if it is a TLS ClientHello.
///
/// Returns `true` if the first byte is 0x16 (TLS record type: Handshake).
pub async fn is_tls_client_hello(stream: &tokio::net::TcpStream) -> bool {
    let mut buf = [0u8; 1];
    match stream.peek(&mut buf).await {
        Ok(1) => buf[0] == 0x16,
        Ok(_) => false,
        Err(e) => {
            warn!(error = %e, "failed to peek first byte");
            false
        }
    }
}
