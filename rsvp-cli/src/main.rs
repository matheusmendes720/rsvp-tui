//! # rsvp — RSVP Speed Reader (native CLI)
//!
//! This is the Rust-native command-line interface for the RSVP
//! speed reader. It uses `clap` derive macros (the Rust
//! equivalent of Python's `Typer`) to expose every workspace
//! task as a subcommand, mirroring the surface that
//! `rsvp_tui.cli` exposes in Python.
//!
//! ## Architecture
//!
//! ```text
//!   ┌─────────────────────────────────────────────────────┐
//!   │  rsvp (Rust binary)                                │
//!   │  ─ Clap CLI                                         │
//!   │  ─ Subprocess orchestrator (spawns the Py TUI)     │
//!   │  ─ Ratatui reader (the high-perf display path)      │
//!   └─────────────────────┬───────────────────────────────┘
//!                         │ subprocess
//!                         ▼
//!   ┌─────────────────────────────────────────────────────┐
//!   │  python -m rsvp_tui.cli (the legacy Textual app)   │
//!   └─────────────────────────────────────────────────────┘
//! ```
//!
//! Subcommands that don't need a TUI (`read --stats`,
//! `library --list`, `doctor`, `version`, `themes`, ...) are
//! fully implemented in Rust and never spawn a Python process.
//! Subcommands that need the full Textual app (`tui`, `read`
//! with no `--stats`, `config`, ...) shell out to the Python
//! CLI via a single subprocess call.

use anyhow::{Context, Result};
use clap::{Parser, Subcommand, ValueHint};
use log::{debug, info};
use std::path::PathBuf;
use std::process::Command;

mod commands;
mod config;
mod output;
pub mod reader;

use commands::*;

/// Top-level CLI for the RSVP speed reader.
///
/// Run with no arguments to launch the interactive TUI. Every
/// other mode (read, import, library, doctor, …) is a
/// subcommand. Use ``rsvp help <subcommand>`` for details on
/// any individual task.
#[derive(Debug, Parser, Clone)]
#[command(
    name = "rsvp",
    version,
    about = "RSVP Speed Reader — read books at 300-1000 WPM in your terminal",
    long_about = None,
    propagate_version = true,
    infer_subcommands = true,
    // Subcommand aliases are short, mnemonic forms. They expand
    // to the canonical subcommand at parse time via the
    // ``alias`` attributes below — so ``rsvp r`` is the same as
    // ``rsvp read``.
    disable_help_subcommand = true,
)]
pub struct Cli {
    /// Optional subcommand. When omitted, the TUI launches.
    #[command(subcommand)]
    pub command: Option<Command_>,

    /// Write a machine-readable JSON report of the operation
    /// (used by the helper scripts and CI).
    #[arg(long, global = true, value_hint = ValueHint::FilePath)]
    pub json_output: Option<PathBuf>,

    /// Increase logging verbosity (``-v`` info, ``-vv`` debug,
    /// ``-vvv`` trace).
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    pub verbose: u8,

    /// Suppress all non-error output. Equivalent to ``--quiet``.
    #[arg(short, long, global = true)]
    pub quiet: bool,
}

/// All subcommands exposed by the CLI.
///
/// New commands should be added here AND in the Python
/// `rsvp_tui.cli` (so users on the legacy Python-only path
/// still get the same surface). The Python side dispatches
/// based on the canonical subcommand name.
#[derive(Debug, Subcommand, Clone)]
pub enum Command_ {
    /// Launch the interactive Textual TUI.
    ///
    /// This is the default when no subcommand is given. The
    /// Rust binary just shells out to ``python -m rsvp_tui.cli``
    /// so users get the full screen, command palette, notes
    /// panel, etc.
    Tui(TuiArgs),

    /// Read a book by file path (imports on first run).
    ///
    /// With no extra flags, this launches the TUI at the
    /// imported book. ``--stats`` prints a non-interactive
    /// summary instead.
    #[command(alias = "r", alias = "open")]
    Read(ReadArgs),

    /// Import a book into the library.
    #[command(alias = "i", alias = "add")]
    Import(ImportArgs),

    /// Manage the book library.
    #[command(alias = "ls", alias = "list")]
    Library(LibraryArgs),

    /// Delete a book from the library.
    #[command(alias = "rm")]
    Remove(RemoveArgs),

    /// Show verbose reading statistics for a book.
    #[command(alias = "info")]
    Stats(StatsArgs),

    /// Open the live settings UI.
    #[command(alias = "cfg")]
    Config(ConfigArgs),

    /// Diagnose the local install: paths, schema, library.
    #[command(alias = "diagnose")]
    Doctor(DoctorArgs),

    /// List the available themes.
    Themes,

    /// Show the data directory paths used by RSVP.
    Where,

    /// Show version, Python, and platform info.
    Version,

    /// Discover and print the workspace task table.
    ///
    /// Reads the same ``pyproject.toml`` the Python side uses
    /// and prints the canonical task surface.
    Tasks,

    /// Print a help message (or ``--help <subcommand>`` for
    /// per-subcommand help).
    #[command(alias = "h", alias = "?")]
    Help(HelpArgs),
}

// ---- Subcommand argument structs -----------------------------------------

#[derive(Debug, Parser, Clone)]
pub struct TuiArgs {
    /// Start in focus mode (no chrome).
    #[arg(short, long)]
    pub focus: bool,
}

#[derive(Debug, Parser, Clone)]
pub struct ReadArgs {
    /// Path to the book file.
    #[arg(value_hint = ValueHint::FilePath)]
    pub file: PathBuf,

    /// Override the reading speed in WPM.
    #[arg(short, long, value_name = "WPM")]
    pub wpm: Option<u32>,

    /// Start at the given word position.
    #[arg(short = 'p', long, default_value_t = 0)]
    pub word: usize,

    /// Start in focus mode.
    #[arg(short, long)]
    pub focus: bool,

    /// Print stats instead of launching the TUI.
    #[arg(long)]
    pub stats: bool,

    /// Use the native Rust/Ratatui reader instead of the
    /// Python Textual TUI. Requires ``--stats`` to be unset
    /// (otherwise the request is a contradiction).
    #[arg(long, conflicts_with = "stats")]
    pub native: bool,
}

#[derive(Debug, Parser, Clone)]
pub struct ImportArgs {
    /// Path to the book file.
    #[arg(value_hint = ValueHint::FilePath)]
    pub file: PathBuf,
}

#[derive(Debug, Parser, Clone)]
pub struct LibraryArgs {
    /// Print a tabular listing to stdout.
    #[arg(short, long)]
    pub list: bool,

    /// Search books by title or author.
    #[arg(short, value_name = "TEXT")]
    pub search: Option<String>,
}

#[derive(Debug, Parser, Clone)]
pub struct RemoveArgs {
    /// ID of the book to remove (or a unique prefix).
    pub book_id: String,

    /// Skip the confirmation prompt.
    #[arg(short, long)]
    pub yes: bool,
}

#[derive(Debug, Parser, Clone)]
pub struct StatsArgs {
    /// ID of the book.
    pub book_id: String,
}

#[derive(Debug, Parser, Clone)]
pub struct ConfigArgs {}

#[derive(Debug, Parser, Clone)]
pub struct DoctorArgs {
    /// Print the report as JSON (for ``rsvp-doctor --json``).
    #[arg(long)]
    pub json: bool,
}

#[derive(Debug, Parser, Clone)]
pub struct HelpArgs {
    /// Subcommand to print help for.
    pub subcommand: Option<String>,
}

// ---- Entry point ----------------------------------------------------------

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialise logging. Honours ``-v`` flags, the ``RUST_LOG``
    // env var, and falls back to a sensible default.
    let log_level = match (cli.quiet, cli.verbose) {
        (true, _) => log::LevelFilter::Error,
        (false, 0) => log::LevelFilter::Warn,
        (false, 1) => log::LevelFilter::Info,
        (false, 2) => log::LevelFilter::Debug,
        (false, _) => log::LevelFilter::Trace,
    };
    env_logger::Builder::from_default_env()
        .filter_level(log_level)
        .format_timestamp_millis()
        .init();

    debug!("cli={:?}", cli);

    // Dispatch. ``None`` means the user typed ``rsvp`` with no
    // arguments, which is the same as ``rsvp tui``.
    let command = cli.command.clone().unwrap_or(Command_::Tui(TuiArgs { focus: false }));

    // Run the actual subcommand.
    let result = run_command(&cli, command);

    if let Err(err) = result {
        if cli.json_output.is_some() {
            // Always emit valid JSON on the error path so
            // scripts can parse it.
            let payload = serde_json::json!({
                "ok": false,
                "error": format!("{err:#}"),
            });
            println!("{}", serde_json::to_string_pretty(&payload)?);
        } else {
            // Render a clean error chain.
            eprintln!("error: {err}");
            for cause in err.chain().skip(1) {
                eprintln!("  caused by: {cause}");
            }
        }
        std::process::ExitCode::from(1);
    }
    Ok(())
}

fn run_command(cli: &Cli, command: Command_) -> Result<()> {
    match &command {
        // Commands that are pure-Rust (no Python required).
        Command_::Doctor(args) => commands::doctor::run(cli, args.clone()),
        Command_::Themes => commands::themes::run(cli),
        Command_::Where => commands::where_cmd::run(cli),
        Command_::Version => commands::version::run(cli),
        Command_::Tasks => commands::tasks::run(cli),
        Command_::Stats(args) => commands::stats::run(cli, args.clone()),
        Command_::Library(args) => commands::library::run(cli, args.clone()),
        Command_::Remove(args) => commands::remove::run(cli, args.clone()),
        Command_::Import(args) => commands::import::run(cli, args.clone()),
        Command_::Help(args) => commands::help::run(cli, args.clone()),

        // Commands that need the full Textual app — shell out.
        Command_::Tui(_) => delegate_to_python(cli, command),
        Command_::Config(_) => delegate_to_python(cli, command),
        Command_::Read(args) if !args.native => delegate_to_python(cli, command),

        // Native Rust/Ratatui reader.
        Command_::Read(args) => {
            let book = read_text_into_book(&args.file, args.wpm.unwrap_or(300))?;
            reader::run_reader(book)
        }
    }
}

/// Load a text-like file into a ``Book`` for the native reader.
fn read_text_into_book(path: &std::path::Path, wpm: u32) -> Result<reader::Book> {
    let raw = std::fs::read_to_string(path)
        .with_context(|| format!("reading {}", path.display()))?;
    let title = path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("Untitled")
        .to_string();
    Ok(reader::book_from_text(&title, &raw, wpm))
}

/// Hand off a subcommand to the Python Textual app.
///
/// The Python ``rsvp_tui.cli`` reads its own ``sys.argv`` and
/// dispatches based on the subcommand name, so this is a
/// straight pass-through. We forward exit code, stdout, and
/// stderr verbatim.
fn delegate_to_python(cli: &Cli, command: Command_) -> Result<()> {
    let mut argv: Vec<String> = vec!["rsvp".to_string()];
    // Re-serialise the clap subcommand into Python argv. We use
    // a dedicated match so we can be explicit about every
    // subcommand and its flags.
    match command {
        Command_::Tui(args) => {
            argv.push("tui".to_string());
            if args.focus {
                argv.push("--focus".to_string());
            }
        }
        Command_::Read(args) => {
            argv.push("read".to_string());
            argv.push(args.file.to_string_lossy().to_string());
            if let Some(wpm) = args.wpm {
                argv.push("--wpm".to_string());
                argv.push(wpm.to_string());
            }
            if args.word > 0 {
                argv.push("--word".to_string());
                argv.push(args.word.to_string());
            }
            if args.focus {
                argv.push("--focus".to_string());
            }
            if args.stats {
                argv.push("--stats".to_string());
            }
        }
        Command_::Config(_) => {
            argv.push("config".to_string());
        }
        _ => unreachable!("delegate_to_python called with non-TUI command"),
    }
    argv.push("--".to_string()); // separator, in case the user adds more

    // Forward the global flags too.
    if cli.quiet {
        argv.push("--quiet".to_string());
    }
    if cli.verbose > 0 {
        argv.push(format!("-{}", "v".repeat(cli.verbose as usize)));
    }

    info!("delegating to Python TUI: {:?}", argv);
    let status = Command::new("python")
        .args(["-m", "rsvp_tui.cli"])
        .args(&argv[1..]) // drop the synthetic "rsvp"
        .status()
        .context("failed to spawn python -m rsvp_tui.cli")?;
    if !status.success() {
        anyhow::bail!("python TUI exited with {}", status);
    }
    Ok(())
}
