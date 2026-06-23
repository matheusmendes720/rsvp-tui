//! `rsvp import` — import a book into the library.

use anyhow::{Context, Result};
use std::process::Command;

use crate::Cli;

pub fn run(_cli: &Cli, args: crate::ImportArgs) -> Result<()> {
    let status = Command::new("python")
        .args([
            "-m",
            "rsvp_tui.cli",
            "import",
            &args.file.to_string_lossy(),
        ])
        .status()
        .context("failed to spawn python -m rsvp_tui.cli import")?;
    if !status.success() {
        anyhow::bail!("python exited with {}", status);
    }
    Ok(())
}
