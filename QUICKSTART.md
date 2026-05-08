# RSVP-TUI Quickstart Guide

## Run the Complete TUI in 3 Steps

---

## Step 1: Build Rust Backend (5 minutes)

```bash
cd rsvp-core

# Install maturin (if not already installed)
pip install maturin

# Build and install Rust extension
maturin develop --release
```

**Verify:**
```bash
python -c "from rsvp_core import calculate_orp_index; print(calculate_orp_index('hello'))"
# Should output: 1
```

---

## Step 2: Install Python TUI (2 minutes)

```bash
cd ../rsvp-tui

# Install in development mode
pip install -e "."

# Or with all optional dependencies
pip install -e ".[all]"
```

**Verify:**
```bash
rsvp --help
# Should show CLI commands
```

---

## Step 3: Launch the TUI (instant)

```bash
# Option 1: Use the installed command
rsvp

# Option 2: Use the launcher
python launch_rsvp.py

# Option 3: Run as module
cd rsvp-tui && python -m rsvp_tui
```

---

## First Use Walkthrough

### 1. Import a Book

```bash
# Import the sample book
rsvp import sample_book.md

# Or import your own file
rsvp import /path/to/your/book.md
```

### 2. Browse Library

```
======================================================================
                              LIBRARY
======================================================================

Search: [                                     ]

 Title                      Author    Progress  Words
 ----------------------------------------------------------------
> The Art of Speed Reading  Unknown   0%        422
 

[Read] [Import] [Delete]

[q] Quit  [?] Help
```

Use arrow keys to navigate, `r` to read selected book.

### 3. Read with RSVP

```
======================================================================
                      The Art of Speed Reading
======================================================================

                              ext[r]aordinary
                                    |
                             [FOCUS]


Word 45/422 (11%) - 300 WPM

[Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [n] Note  [f] Focus
```

**Controls:**
- `Space` - Start/pause reading
- `←/→` - Navigate words manually
- `↑/↓` - Change speed (100-1000 WPM)
- `n` - Add note at current position
- `o` - Toggle ORP highlighting
- `f` - Toggle focus mode

### 4. Add Notes

Press `n` while reading:

```
======================================================================
                          ADD NOTE
======================================================================

Position: Word 45
Context: 'speed'

Tags: [key-concept, rsvp            ]

Content:
+--------------------------------------------------+
| RSVP eliminates eye movements - key insight!     |
+--------------------------------------------------+

            [Cancel]    [Save]
```

Notes are:
- Linked to exact word position
- Searchable by tags
- Exportable to Markdown

---

## CLI Commands Reference

```bash
# Launch interactive TUI
rsvp

# Import a book
rsvp import ./my-book.md

# List all books
rsvp library --list

# Search books
rsvp library --search "python"

# Show book stats
rsvp stats book_id

# Read with options
rsvp read book.md --wpm 400 --focus
```

---

## Troubleshooting

### Rust Import Error

```
ImportError: cannot import name 'rsvp_core'
```

**Fix:**
```bash
cd rsvp-core
maturin develop --release
```

### Textual Display Issues

```
Terminal doesn't support required features
```

**Fix:**
- Use a modern terminal (Windows Terminal, iTerm2, GNOME Terminal)
- Set `TERM=xterm-256color`

### Unicode Errors

```
UnicodeEncodeError: can't encode character
```

**Fix:**
```bash
export PYTHONIOENCODING=utf-8
# On Windows:
chcp 65001
```

---

## Configuration

Edit `~/.rsvp/config.json`:

```json
{
    "default_wpm": 300,
    "enable_orp": true,
    "pause_on_punctuation": true,
    "punctuation_multiplier": 2.0,
    "focus_mode": false
}
```

---

## File Locations

| Data | Location |
|------|----------|
| Config | `~/.rsvp/config.json` |
| Library DB | `~/.rsvp/library.db` |
| Notes | `~/.rsvp/notes/` |
| Cache | `~/.rsvp/cache/` |

---

## Keyboard Shortcuts Cheat Sheet

### Global
```
? = Help
q = Quit
l = Library
```

### Library
```
↑/↓ = Navigate
r = Read selected
i = Import
s = Search
d = Delete
```

### Reader
```
Space = Play/Pause
←/→ = Skip word
↑/↓ = Speed
n = Add note
o = Toggle ORP
f = Focus mode
r = Restart
Tab = Toggle notes
Esc = Back to library
```

---

## Demo Without Installation

Run the standalone demo:

```bash
python demo_tui.py
```

This runs a simplified version without full dependencies.

---

## Support

- **Issues:** Check TUI_FEATURES.md for detailed docs
- **Architecture:** See ARCHITECTURE_SUMMARY.md
- **Development:** See PRD.md for full specs

---

**Happy Speed Reading!** 📖⚡
