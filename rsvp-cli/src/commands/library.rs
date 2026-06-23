//! `rsvp library` — manage the book library (list, search).

use anyhow::{Context, Result};
use std::process::Command;

use crate::Cli;

pub fn run(_cli: &Cli, args: crate::LibraryArgs) -> Result<()> {
    let mut argv: Vec<String> = vec!["library".to_string()];
    if args.list {
        argv.push("--list".to_string());
    }
    if let Some(s) = &args.search {
        argv.push("--search".to_string());
        argv.push(s.clone());
    }
    let status = Command::new("python")
        .args(["-m", "rsvp_tui.cli"])
        .args(&argv)
        .status()
        .context("failed to spawn python -m rsvp_tui.cli library")?;
    if !status.success() {
        anyhow::bail!("python exited with {}", status);
    }
    Ok(())
}
