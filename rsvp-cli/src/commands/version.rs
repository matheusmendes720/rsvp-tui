//! `rsvp version` — print version, platform, rust-core status.

use crate::output::report;
use crate::Cli;

pub fn run(cli: &Cli) -> anyhow::Result<()> {
    let pkg_version = env!("CARGO_PKG_VERSION");
    let platform = format!("{}-{}", std::env::consts::OS, std::env::consts::ARCH);
    let py_version = python_version().unwrap_or_else(|| "n/a".to_string());

    let plain = format!(
        "  rsvp           {pkg_version}\n  python         {py_version}\n  platform       {platform}\n  rust_core      {}\n",
        rust_core_status()
    );
    report(
        cli,
        serde_json::json!({
            "rsvp": pkg_version,
            "python": py_version,
            "platform": platform,
            "rust_core": rust_core_status(),
        }),
        &plain,
    )
}

fn python_version() -> Option<String> {
    let out = std::process::Command::new("python")
        .args(["-c", "import sys; print(sys.version.split()[0])"])
        .output()
        .ok()?;
    if out.status.success() {
        Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
    } else {
        None
    }
}

fn rust_core_status() -> &'static str {
    if std::process::Command::new("python")
        .args(["-c", "import rsvp_core; print('ok')"])
        .output()
        .map(|o| o.status.success() && String::from_utf8_lossy(&o.stdout).contains("ok"))
        .unwrap_or(false)
    {
        "available"
    } else {
        "fallback"
    }
}
