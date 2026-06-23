import pytest
from rsvp_tui import (
    tokenize_text,
    calculate_orp_index,
    calculate_word_delay,
    split_word_for_display,
    estimate_reading_time,
)

def test_tokenization():
    text = "Hello, world! This is a test."
    words = tokenize_text(text)
    assert len(words) == 6
    assert words[0] == "Hello,"
    assert words[-1] == "test."

def test_orp_calculation():
    assert calculate_orp_index("a") == 0
    assert calculate_orp_index("the") == 0
    assert calculate_orp_index("hello") == 1
    assert calculate_orp_index("reading") == 2
    assert calculate_orp_index("extraordinary") == 3

def test_word_splitting():
    # Test 'hello' -> ORP at index 1 ('e')
    parts = split_word_for_display("hello", 1)
    assert parts.before_orp == "h"
    assert parts.orp_char == "e"
    assert parts.after_orp == "llo"

def test_word_delay():
    wpm = 300  # 60000 / 300 = 200ms base delay
    pause_chars = ['.', '!', '?']
    
    # Normal word
    assert calculate_word_delay("word", wpm, 2.0, pause_chars) == 200
    
    # Word with punctuation (2.0x multiplier)
    assert calculate_word_delay("word.", wpm, 2.0, pause_chars) == 400

def test_reading_time_estimation():
    # 300 words at 300 WPM = 1 minute
    mins, secs = estimate_reading_time(300, 300)
    assert mins == 1
    assert secs == 0
    
    # 450 words at 300 WPM = 1.5 minutes = 1 min 30 sec
    mins, secs = estimate_reading_time(450, 300)
    assert mins == 1
    assert secs == 30
