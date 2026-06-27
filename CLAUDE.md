<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **rspv** (1733 symbols, 3104 relationships, 131 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/rspv/context` | Codebase overview, check index freshness |
| `gitnexus://repo/rspv/clusters` | All functional areas |
| `gitnexus://repo/rspv/processes` | All execution flows |
| `gitnexus://repo/rspv/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |
| Work in the Rsvp_tui area (96 symbols) | `.claude/skills/generated/rsvp-tui/SKILL.md` |
| Work in the Components area (54 symbols) | `.claude/skills/generated/components/SKILL.md` |
| Work in the Widgets area (37 symbols) | `.claude/skills/generated/widgets/SKILL.md` |
| Work in the Rsvp-reader area (26 symbols) | `.claude/skills/generated/rsvp-reader/SKILL.md` |
| Work in the Managers area (20 symbols) | `.claude/skills/generated/managers/SKILL.md` |
| Work in the Cluster_4 area (7 symbols) | `.claude/skills/generated/cluster-4/SKILL.md` |
| Work in the Pages area (7 symbols) | `.claude/skills/generated/pages/SKILL.md` |
| Work in the Cluster_89 area (6 symbols) | `.claude/skills/generated/cluster-89/SKILL.md` |
| Work in the Cluster_6 area (5 symbols) | `.claude/skills/generated/cluster-6/SKILL.md` |
| Work in the Cluster_78 area (5 symbols) | `.claude/skills/generated/cluster-78/SKILL.md` |
| Work in the Cluster_87 area (5 symbols) | `.claude/skills/generated/cluster-87/SKILL.md` |
| Work in the Cluster_94 area (5 symbols) | `.claude/skills/generated/cluster-94/SKILL.md` |
| Work in the Cluster_5 area (4 symbols) | `.claude/skills/generated/cluster-5/SKILL.md` |
| Work in the Cluster_73 area (4 symbols) | `.claude/skills/generated/cluster-73/SKILL.md` |
| Work in the Cluster_85 area (4 symbols) | `.claude/skills/generated/cluster-85/SKILL.md` |
| Work in the Cluster_86 area (4 symbols) | `.claude/skills/generated/cluster-86/SKILL.md` |
| Work in the Misc area (3 symbols) | `.claude/skills/generated/misc/SKILL.md` |
| Work in the Cluster_61 area (3 symbols) | `.claude/skills/generated/cluster-61/SKILL.md` |
| Work in the Cluster_77 area (3 symbols) | `.claude/skills/generated/cluster-77/SKILL.md` |
| Work in the Cluster_91 area (3 symbols) | `.claude/skills/generated/cluster-91/SKILL.md` |

<!-- gitnexus:end -->
