//! `rsvp themes` — list the available themes.

use anyhow::Result;
use serde::Serialize;

use crate::output::report;
use crate::Cli;

#[derive(Debug, Serialize)]
pub struct Theme {
    pub id: String,
    pub name: String,
}

/// Theme catalogue. Mirrors ``rsvp_tui.themes.all_themes()`` —
/// when a theme is added there, add it here too.
const CATALOG: &[(&str, &str)] = &[
    ("dark", "Dark (default)"),
    ("light", "Light"),
    ("solarized", "Solarized"),
    ("monokai", "Monokai"),
    ("solarized-dark", "Solarized Dark"),
    ("gruvbox", "Gruvbox"),
    ("nord", "Nord"),
    ("dracula", "Dracula"),
];

pub fn run(cli: &Cli) -> Result<()> {
    let themes: Vec<Theme> = CATALOG
        .iter()
        .map(|(id, name)| Theme { id: id.to_string(), name: name.to_string() })
        .collect();
    let current = current_theme_id().unwrap_or_else(|| "dark".to_string());
    let mut plain = String::from("Current: ");
    plain.push_str(&current);
    plain.push_str("\n\n");
    plain.push_str(&format!("{:<14} {:<20}\n", "ID", "Name"));
    plain.push_str(&"-".repeat(34));
    plain.push('\n');
    for t in &themes {
        let marker = if t.id == current { "*" } else { " " };
        plain.push_str(&format!("{} {:<12} {}\n", marker, t.id, t.name));
    }
    report(
        cli,
        serde_json::json!({ "current": current, "themes": themes }),
        &plain,
    )
}

fn current_theme_id() -> Option<String> {
    let raw = crate::config::read_config().ok()?;
    raw.get("theme")
        .and_then(|v| v.get("id"))
        .and_then(|v| v.as_str())
        .map(String::from)
}
