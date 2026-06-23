//! Configuration discovery shared by every subcommand.
//!
//! Mirrors the ``Config`` Pydantic model in the Python side:
//! the canonical paths live in the ``RSVP_HOME`` directory
//! (defaulting to ``~/.rsvp``). We expose helpers that read
//! and validate those paths; we never mutate them from Rust —
//! the Python side is the source of truth for writes.

use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

/// Where RSVP keeps its data on disk. Mirrors the Python
/// ``Config`` ``home_dir`` property.
pub fn home_dir() -> PathBuf {
    std::env::var_os("RSVP_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            dirs_home().map(|h| h.join(".rsvp")).unwrap_or_else(|| PathBuf::from(".rsvp"))
        })
}

/// The platform-specific user home directory.
///
/// We don't pull in the ``dirs`` crate for this — the logic is
/// trivial and avoiding the dependency keeps the build small.
pub fn dirs_home() -> Option<PathBuf> {
    if let Some(profile) = std::env::var_os("USERPROFILE") {
        return Some(PathBuf::from(profile));
    }
    if let Some(home) = std::env::var_os("HOME") {
        return Some(PathBuf::from(home));
    }
    None
}

/// All canonical RSVP paths in one place.
#[derive(Debug, Clone)]
pub struct Paths {
    pub home: PathBuf,
    pub config_file: PathBuf,
    pub library_db: PathBuf,
    pub notes_dir: PathBuf,
    pub cache_dir: PathBuf,
}

impl Paths {
    pub fn discover() -> Result<Self> {
        let home = home_dir();
        Ok(Self {
            config_file: home.join("config.json"),
            library_db: home.join("library.db"),
            notes_dir: home.join("notes"),
            cache_dir: home.join("cache"),
            home,
        })
    }

    /// Print a one-line status for each path. ``marker`` is
    /// ``✓`` when the path exists and ``·`` otherwise.
    pub fn render_table(&self) -> String {
        let mut out = String::new();
        out.push_str("RSVP data locations:\n\n");
        for (label, path) in self.iter() {
            let marker = if Path::new(path).exists() { "✓" } else { "·" };
            out.push_str(&format!("  {marker} {label:<14} {}\n", path.display()));
        }
        out
    }

    fn iter(&self) -> impl Iterator<Item = (&'static str, &Path)> {
        [
            ("Config file", self.config_file.as_path()),
            ("Library DB", self.library_db.as_path()),
            ("Notes dir", self.notes_dir.as_path()),
            ("Cache dir", self.cache_dir.as_path()),
            ("Home", self.home.as_path()),
        ]
        .into_iter()
    }
}

/// Read the config file and return the raw JSON string, or
/// an empty object if the file doesn't exist yet.
pub fn read_config() -> Result<serde_json::Value> {
    let paths = Paths::discover()?;
    if !paths.config_file.exists() {
        return Ok(serde_json::json!({}));
    }
    let raw = std::fs::read_to_string(&paths.config_file)
        .with_context(|| format!("reading config from {}", paths.config_file.display()))?;
    let value: serde_json::Value = serde_json::from_str(&raw)
        .with_context(|| format!("parsing config at {}", paths.config_file.display()))?;
    Ok(value)
}
