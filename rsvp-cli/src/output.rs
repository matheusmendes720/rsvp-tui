//! Shared output formatting helpers.
//!
//! Subcommands that need to print a human-readable table or a
//! machine-readable JSON report use the helpers in this module
//! so the formatting is consistent.

use anyhow::Result;
use std::path::Path;

/// Print a status line to stdout: either a plain string or a
/// JSON object if ``--json-output`` is set on the CLI.
pub fn report(cli: &super::Cli, payload: serde_json::Value, plain: &str) -> Result<()> {
    if let Some(path) = &cli.json_output {
        if let Some(parent) = path.parent() {
            if !parent.as_os_str().is_empty() {
                std::fs::create_dir_all(parent).ok();
            }
        }
        let json = serde_json::to_string_pretty(&payload)?;
        std::fs::write(path, json).map_err(|e| {
            anyhow::anyhow!("writing report to {}: {e}", path.display())
        })?;
    }
    if !cli.quiet {
        println!("{plain}");
    }
    Ok(())
}

/// Print a yellow "warning" line to stderr.
pub fn warn(msg: impl AsRef<str>) {
    eprintln!("warning: {}", msg.as_ref());
}

/// Print a red "error" line to stderr.
pub fn err(msg: impl AsRef<str>) {
    eprintln!("error: {}", msg.as_ref());
}
