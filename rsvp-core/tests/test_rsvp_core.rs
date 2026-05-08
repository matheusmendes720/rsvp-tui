use rsvp_core::rsvp_core::*;

#[test]
fn test_calculate_orp_index() {
    assert_eq!(calculate_orp_index("a"), 0);
    assert_eq!(calculate_orp_index("the"), 0);
    assert_eq!(calculate_orp_index("word"), 1);
    assert_eq!(calculate_orp_index("reading"), 2);
    assert_eq!(calculate_orp_index("extraordinary"), 3);
}

#[test]
fn test_calculate_word_delay() {
    // At 300 WPM, base delay = 200ms
    let delay = calculate_word_delay("hello", 300, 2.0, &['.', '!', '?']);
    assert_eq!(delay, 200);
    
    // With punctuation, should be 400ms
    let delay = calculate_word_delay("hello!", 300, 2.0, &['.', '!', '?']);
    assert_eq!(delay, 400);
}

#[test]
fn test_estimate_reading_time() {
    assert_eq!(estimate_reading_time(300, 300), (1, 0));
    assert_eq!(estimate_reading_time(150, 300), (0, 30));
}

#[test]
fn test_split_word_for_display() {
    let parts = split_word_for_display("hello", 1);
    assert_eq!(parts.before_orp, "h");
    assert_eq!(parts.orp_char, "e");
    assert_eq!(parts.after_orp, "llo");
}
