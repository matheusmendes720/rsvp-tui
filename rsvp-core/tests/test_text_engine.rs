use rsvp_core::text_engine::*;

#[test]
fn test_tokenize_text() {
    let text = "Hello, world! This is a test.";
    let words = tokenize_text(text);
    assert_eq!(words, vec!["Hello,", "world!", "This", "is", "a", "test."]);
}

#[test]
fn test_normalize_whitespace() {
    assert_eq!(
        normalize_whitespace("  Hello    world  "),
        "Hello world"
    );
}

#[test]
fn test_calculate_reading_complexity() {
    let text = "The cat sat on the mat.";
    let score = calculate_reading_complexity(text);
    assert!(score > 0.0);
}

#[test]
fn test_count_syllables() {
    assert_eq!(count_syllables("hello"), 2);
    assert_eq!(count_syllables("world"), 1);
    assert_eq!(count_syllables("extraordinary"), 5);
}
