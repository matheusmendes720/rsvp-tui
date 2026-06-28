from rsvp_tui import fallbacks


def test_fallback_tokenization():
    text = "Hello, world! This is a test."
    words = fallbacks.tokenize_text(text)
    assert len(words) == 6
    assert words[0] == "Hello,"


def test_fallback_orp_calculation():
    assert fallbacks.calculate_orp_index("a") == 0
    assert fallbacks.calculate_orp_index("the") == 0
    assert fallbacks.calculate_orp_index("hello") == 1
    assert fallbacks.calculate_orp_index("reading") == 2


def test_fallback_word_delay():
    wpm = 300
    pause_chars = [".", "!", "?"]
    assert fallbacks.calculate_word_delay("word", wpm, 2.0, pause_chars) == 200
    assert fallbacks.calculate_word_delay("word.", wpm, 2.0, pause_chars) == 400


def test_fallback_markdown_parsing():
    content = "# Chapter 1\n\nWord1 Word2."
    result = fallbacks.parse_markdown(content)
    assert result.title == "Chapter 1"
    assert result.word_count == 2
    assert len(result.chapters) == 1
