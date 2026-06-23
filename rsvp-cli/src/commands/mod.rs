//! Subcommand implementations for the rsvp CLI.
//!
//! One module per subcommand. Every public function takes a
//! reference to the parsed top-level ``Cli`` (so it can read
//! global flags like ``--json-output`` / ``-v``) and the
//! subcommand-specific args struct.

pub mod doctor;
pub mod help;
pub mod import;
pub mod library;
pub mod remove;
pub mod stats;
pub mod tasks;
pub mod themes;
pub mod version;
pub mod where_cmd;
