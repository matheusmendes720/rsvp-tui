#!/usr/bin/env python3
"""
Launcher script for RSVP TUI.
Run this to start the interactive speed reader!
"""

import sys
from pathlib import Path

# Add rsvp-tui to path
sys.path.insert(0, str(Path(__file__).parent / "rsvp-tui"))

try:
    from rsvp_tui.app_complete import RSVPTUI
    
    print("=" * 70)
    print("🚀 RSVP Speed Reader - Interactive TUI")
    print("=" * 70)
    print()
    print("Features:")
    print("  📚 Library management with SQLite")
    print("  📖 RSVP reading with ORP highlighting")
    print("  📝 Position-linked note-taking")
    print("  ⚡ Rust backend for performance")
    print()
    print("Keyboard shortcuts:")
    print("  Space = Play/Pause  ←/→ = Skip  ↑/↓ = Speed")
    print("  n = Add note        o = Toggle ORP  f = Focus mode")
    print("  l = Library         ? = Help        q = Quit")
    print()
    print("Press Ctrl+C to exit at any time")
    print("=" * 70)
    print()
    
    app = RSVPTUI()
    app.run()
    
except ImportError as e:
    print(f"❌ Error importing RSVP modules: {e}")
    print()
    print("Make sure to install dependencies:")
    print("  cd rsvp-tui && pip install -e .")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n\n👋 Goodbye!")
    sys.exit(0)
