# RSVP Core

High-performance Rust library for RSVP speed reading with Python bindings via PyO3.

## Modules

- **text_engine**: Text tokenization, normalization, complexity analysis
- **rsvp_core**: ORP calculation, timing, display logic
- **file_parser**: PDF, EPUB, Markdown parsing
- **word_stats**: Frequency analysis, difficulty scoring

## Building

```bash
# Build Rust library
cargo build --release

# Run tests
cargo test

# Run benchmarks
cargo bench

# Build Python extension
maturin develop
# or
pip install -e .
```

## Python API

```python
from rsvp_core import (
    tokenize_text,
    parse_markdown,
    calculate_orp_index,
    calculate_word_delay,
)

# Tokenize text
words = tokenize_text("Hello world! This is a test.")

# Parse markdown
result = parse_markdown("# Title\n\nContent here...")
print(result.title)  # "Title"
print(result.word_count)

# Calculate ORP
orp = calculate_orp_index("reading")  # Returns: 2

# Calculate display delay
delay_ms = calculate_word_delay("word.", wpm=300, punctuation_multiplier=2.0)
```
