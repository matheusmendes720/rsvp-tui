# Security policy

## Supported versions

The `master` branch of this repository is the only supported
version. We do not backport security fixes to older branches.

## Reporting a vulnerability

Please **do not** file a public issue. Instead, email
`security@rsvp.example` (replace with the real address) with:

- A description of the vulnerability
- A proof-of-concept or reproduction steps
- The affected version (commit hash or tag)

We will acknowledge receipt within 48 hours and aim to ship
a fix within 7 days. Critical issues are handled faster.

## Scope

In-scope:

- The Python `rsvp-tui` package
- The Rust `rsvp-core` and `rsvp-cli` crates
- The workspace helper scripts in `scripts/`

Out-of-scope:

- Third-party dependencies — please report to the upstream
  maintainers directly.
- The user-configured `~/.rsvp/` directory on your local
  machine.

## Disclosure

We follow a 90-day coordinated disclosure policy. After a fix
is released, the vulnerability will be published in the GitHub
Security Advisories database.
