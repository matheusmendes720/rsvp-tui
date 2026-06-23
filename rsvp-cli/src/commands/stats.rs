//! `rsvp stats` — show reading statistics for a book.
//!
//! This is a thin wrapper that shells out to the Python
//! ``rsvp_tui.cli stats`` so we don't have to re-implement the
//! SQLite query in Rust. The Python side already prints a
//! well-formatted, complete report.

use anyhow::{Context, Result};
use std::process::Command;

use crate::Cli;

pub fn run(_cli: &Cli, args: crate::StatsArgs) -> Result<()> {
    let status = Command::new("python")
        .args(["-m", "rsvp_tui.cli", "stats", &args.book_id])
        .status()
        .context("failed to spawn python -m rsvp_tui.cli stats")?;
    if !status.success() {
        anyhow::bail!("python exited with {}", status);
    }
    Ok(())
}
