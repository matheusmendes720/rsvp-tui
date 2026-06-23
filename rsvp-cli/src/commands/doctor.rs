//! `rsvp doctor` — diagnose the local install.

use anyhow::Result;
use chrono::Utc;
use serde::Serialize;

use crate::config::Paths;
use crate::output::report;
use crate::Cli;

#[derive(Debug, Serialize)]
pub struct DoctorReport {
    pub ok: bool,
    pub version: String,
    pub platform: String,
    pub rust_core: &'static str,
    pub home_dir: String,
    pub config_exists: bool,
    pub config_path: String,
    pub library_exists: bool,
    pub library_path: String,
    pub notes_exists: bool,
    pub notes_path: String,
    pub timestamp: String,
}

pub fn run(cli: &Cli, args: crate::DoctorArgs) -> Result<()> {
    let paths = Paths::discover()?;
    let rust_core = rust_core_status();
    let report_data = DoctorReport {
        ok: true,
        version: env!("CARGO_PKG_VERSION").to_string(),
        platform: format!("{} ({})", std::env::consts::OS, std::env::consts::ARCH),
        rust_core,
        home_dir: paths.home.display().to_string(),
        config_exists: paths.config_file.exists(),
        config_path: paths.config_file.display().to_string(),
        library_exists: paths.library_db.exists(),
        library_path: paths.library_db.display().to_string(),
        notes_exists: paths.notes_dir.exists(),
        notes_path: paths.notes_dir.display().to_string(),
        timestamp: Utc::now().to_rfc3339(),
    };

    if args.json {
        println!("{}", serde_json::to_string_pretty(&report_data)?);
    } else {
        report(
            cli,
            serde_json::to_value(&report_data)?,
            &format!(
                "{}\n\n  version:        {}\n  platform:       {}\n  rust_core:      {}\n  home:           {}\n  config:         {}\n  library_db:     {}\n  notes_dir:      {}\n",
                report_data.timestamp,
                report_data.version,
                report_data.platform,
                report_data.rust_core,
                if report_data.home_dir.is_empty() { "?" } else { &report_data.home_dir },
                if report_data.config_exists { "✓ exists" } else { "· missing" },
                if report_data.library_exists { "✓ exists" } else { "· missing" },
                if report_data.notes_exists { "✓ exists" } else { "· missing" },
            ),
        )?;
    }
    Ok(())
}

fn rust_core_status() -> &'static str {
    // Probe the optional Rust core by trying to import it. We
    // don't fail the whole doctor on a missing import — the
    // Python fallbacks cover the case.
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
