//! `rsvp tasks` — print the workspace task table.
//!
//! Reads the workspace ``pyproject.toml`` (if it exists) and
//! prints every ``[project.scripts]`` entry as a task. The
//! description column is looked up from a hard-coded map (so
//! the output matches the Python ``scripts.tasks`` table).
//!
//! Falls back to a hand-rolled table if the ``pyproject.toml``
//! is missing (e.g. when running outside the workspace).

use anyhow::Result;
use std::collections::BTreeMap;
use std::path::Path;

use crate::output::report;
use crate::Cli;

const DESCRIPTIONS: &[(&str, &str)] = &[
    ("rsvp-tasks", "Print this task table"),
    ("rsvp-tui", "Launch the interactive TUI (default)"),
    ("rsvp-palette", "Open the in-TUI command palette"),
    ("rsvp-demo", "Launch the dependency-free standalone demo"),
    ("rsvp-build", "Build the Rust extension + install the Python pkg"),
    ("rsvp-dev", "Editable install (maturin develop --release)"),
    ("rsvp-sync", "uv sync (optionally --rebuild the Rust ext)"),
    ("rsvp-clean", "Remove build/, dist/, __pycache__, eggs, caches"),
    ("rsvp-test", "Run the pytest suite (extras forwarded)"),
    ("rsvp-lint", "ruff check + black --check"),
    ("rsvp-format", "black + ruff --fix"),
    ("rsvp-typecheck", "mypy --strict"),
    ("rsvp-verify", "lint + typecheck + test (full quality gate)"),
    ("rsvp-docs", "Build man page + snapshot CLI help"),
    ("rsvp-man", "Render / view / install rsvp.1"),
    ("rsvp-bench", "Run cargo benchmarks (Rust micro-benchmarks)"),
    ("rsvp-read", "Read a book by file path (alias: r)"),
    ("rsvp-import", "Import a book into the library (alias: i)"),
    ("rsvp-library", "Manage the book library (alias: ls)"),
    ("rsvp-config", "Open the live settings UI"),
];

pub fn run(cli: &Cli) -> Result<()> {
    // Look up the workspace pyproject.toml by walking up from
    // the current executable's directory. We try a few common
    // locations.
    let candidates = [
        "pyproject.toml",
        "../pyproject.toml",
        "../../pyproject.toml",
    ];
    let mut scripts: BTreeMap<String, String> = BTreeMap::new();
    for c in &candidates {
        if Path::new(c).exists() {
            if let Ok(map) = parse_scripts_from_pyproject(Path::new(c)) {
                scripts = map;
                break;
            }
        }
    }
    if scripts.is_empty() {
        // Fall back to the hard-coded map.
        for (name, desc) in DESCRIPTIONS {
            scripts.insert((*name).to_string(), (*desc).to_string());
        }
    }

    let width = scripts.keys().map(|k| k.len()).max().unwrap_or(8);
    let mut plain = String::new();
    plain.push('\n');
    plain.push_str("  rsvp workspace — uv run task surface\n");
    plain.push_str(&format!("  {}\n", "-".repeat(width + 56)));
    plain.push_str(&format!(
        "  {:<width$}  {:<32}  description\n",
        "task", "runner"
    ));
    plain.push_str(&format!("  {}\n", "-".repeat(width + 56)));
    for (name, _desc) in &scripts {
        let lookup_desc = DESCRIPTIONS
            .iter()
            .find(|(n, _)| *n == name.as_str())
            .map(|(_, d)| *d)
            .unwrap_or("—");
        let runner = format!("{name}:main (or fallback)");
        plain.push_str(&format!(
            "  {name:<width$}  {runner:<32}  {lookup_desc}\n"
        ));
    }
    plain.push_str(&format!("\n  {} tasks available\n", scripts.len()));
    report(cli, serde_json::json!({ "tasks": scripts }), &plain)
}

/// Best-effort TOML parser for ``[project.scripts]``.
///
/// Uses a tiny hand-rolled reader to avoid pulling in a TOML
/// crate (the rest of the binary is intentionally lean). We
/// only extract the table values that look like ``name = "mod:fn"``;
/// every other line is ignored.
fn parse_scripts_from_pyproject(path: &Path) -> Result<BTreeMap<String, String>> {
    let raw = std::fs::read_to_string(path)?;
    let mut out = BTreeMap::new();
    let mut in_scripts = false;
    for line in raw.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if trimmed.starts_with('[') {
            in_scripts = trimmed == "[project.scripts]";
            continue;
        }
        if !in_scripts {
            continue;
        }
        if let Some((k, v)) = parse_kv(trimmed) {
            out.insert(k, v);
        }
    }
    Ok(out)
}

fn parse_kv(line: &str) -> Option<(String, String)> {
    let eq = line.find('=')?;
    let (k, v) = line.split_at(eq);
    let k = k.trim().to_string();
    let v = v[1..].trim();
    // Strip surrounding quotes
    let v = v
        .strip_prefix('"')
        .and_then(|s| s.strip_suffix('"'))
        .or_else(|| v.strip_prefix('\'').and_then(|s| s.strip_suffix('\'')))
        .unwrap_or(v)
        .to_string();
    if k.is_empty() {
        None
    } else {
        Some((k, v))
    }
}
