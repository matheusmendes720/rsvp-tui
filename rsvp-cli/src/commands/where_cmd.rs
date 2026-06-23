//! `rsvp where` — print the data directory paths.

use crate::config::Paths;
use crate::output::report;
use crate::Cli;

pub fn run(cli: &Cli) -> anyhow::Result<()> {
    let paths = Paths::discover()?;
    report(
        cli,
        serde_json::json!({
            "home": paths.home,
            "config": paths.config_file,
            "library_db": paths.library_db,
            "notes_dir": paths.notes_dir,
            "cache_dir": paths.cache_dir,
        }),
        &paths.render_table(),
    )
}
