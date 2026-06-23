//! `rsvp help` — print help for a subcommand (or top-level).

use anyhow::Result;
use clap::CommandFactory;

use crate::Cli;

pub fn run(_cli: &Cli, args: crate::HelpArgs) -> Result<()> {
    if let Some(name) = args.subcommand {
        // Find the matching subcommand and print its help.
        let mut cmd = Cli::command();
        if let Some(sub) = cmd.find_subcommand_mut(&name) {
            sub.print_help()?;
            println!();
        } else {
            eprintln!("error: no such subcommand: {name}");
            std::process::exit(2);
        }
    } else {
        // Top-level help.
        let mut cmd = Cli::command();
        cmd.print_help()?;
        println!();
    }
    Ok(())
}
