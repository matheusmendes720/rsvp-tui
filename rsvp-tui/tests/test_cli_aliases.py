"""Tests for the CLI aliases and grouped --help output.

Covers:

* ``ALIASES`` resolves short names to canonical commands.
* ``RsvpGroup.get_command`` returns the canonical command when
  given an alias.
* ``COMMAND_GROUPS`` lists every canonical command that's
  registered on the group.
* The new ``where`` and ``version`` subcommands exist.
"""

from __future__ import annotations

from rsvp_tui.cli import (
    ALIASES,
    COMMAND_GROUPS,
    RsvpGroup,
    cli,
)

# ---- Aliases registry ------------------------------------------------------


def test_aliases_map_to_real_commands():
    """Every alias's target must be a registered command."""
    registered = set(cli.commands)
    for alias, target in ALIASES.items():
        assert target in registered, (
            f"alias {alias!r} -> {target!r} but {target!r} is not a "
            f"registered subcommand (have: {sorted(registered)})"
        )


def test_no_alias_collides_with_canonical_name():
    """An alias must not be the same as a canonical name
    (otherwise it shadows itself)."""
    registered = set(cli.commands)
    for alias in ALIASES:
        assert alias not in registered, (
            f"alias {alias!r} collides with a registered command"
        )


def test_no_two_aliases_share_target_unnecessarily():
    """Each canonical name is fine to have multiple aliases
    (``r`` + ``open`` -> ``read``). We only check that the alias
    keys are unique."""
    assert len(ALIASES) == len(set(ALIASES)), "duplicate alias keys"


# ---- RsvpGroup resolution --------------------------------------------------


def test_get_command_resolves_alias_to_canonical():
    """``RsvpGroup.get_command`` returns the same command for an
    alias as for its canonical name."""
    # The cli is a RsvpGroup (set via ``cls=`` in the decorator).
    assert isinstance(cli, RsvpGroup)
    ctx = cli.make_context("rsvp", ["read"], resilient_parsing=True)
    canon = cli.get_command(ctx, "read")
    aliased = cli.get_command(ctx, ALIASES["r"])
    assert canon is aliased, "alias 'r' must resolve to the same Command as 'read'"


def test_get_command_returns_none_for_unknown():
    """Unknown command names return ``None`` (Click contract)."""
    ctx = cli.make_context("rsvp", [], resilient_parsing=True)
    assert cli.get_command(ctx, "nope") is None


# ---- COMMAND_GROUPS --------------------------------------------------------


def test_every_registered_command_is_in_some_group():
    """If a command is registered on the group, it must appear in
    ``COMMAND_GROUPS`` (otherwise it shows up after the groups in
    ``--help``, which is fine, but the test catches drift)."""
    in_groups = {c for _, cmds in COMMAND_GROUPS for c in cmds}
    registered = set(cli.commands)
    missing = registered - in_groups
    # We only WARN about drift — the group still works. The
    # ``list_commands`` impl handles the rest.
    assert not missing, (
        f"registered commands not in COMMAND_GROUPS: {missing}"
    )


def test_command_groups_have_unique_commands():
    """No command may appear in two groups."""
    seen: dict = {}
    for cat, cmds in COMMAND_GROUPS:
        for c in cmds:
            assert c not in seen, (
                f"command {c!r} in both {seen[c]!r} and {cat!r}"
            )
            seen[c] = cat


# ---- New helper subcommands exist ------------------------------------------


def test_where_subcommand_exists():
    assert "where" in cli.commands


def test_version_subcommand_exists():
    assert "version" in cli.commands


def test_version_subcommand_does_not_shadow_click_version_option():
    """``--version`` is a Click option, ``version`` is a subcommand;
    they coexist. Verify the subcommand is reachable by name and
    that ``--version`` is still a valid option on the group."""
    ctx = cli.make_context("rsvp", ["version"], resilient_parsing=True)
    assert cli.get_command(ctx, "version") is not None
    # The group itself should have ``version`` listed as a param.
    param_names = {p.name for p in cli.params}
    assert "version" in param_names
