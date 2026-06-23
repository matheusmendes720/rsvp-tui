//! `rsvp remove` — delete a book from the library.

use anyhow::{Context, Result};
use std::process::Command;

use crate::Cli;

pub fn run(_cli: &Cli, args: crate::RemoveArgs) -> Result<()> {
    let mut argv: Vec<String> = vec!["remove".to_string(), args.book_id.clone()];
    if args.yes {
        argv.push("--yes".to_string());
    }
    let status = Command::new("python")
        .args(["-m", "rsvp_tui.cli"])
        .args(&argv)
        .status()
        .context("failed to spawn python -m rsvp_tui.cli remove")?;
    if !status.success() {
        anyhow::bail!("python exited with {}", status);
    }
    Ok(())
}
