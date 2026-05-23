from services.text_preprocessor import preprocess_text


def test_preprocess_normalizes_dashes_and_quotes():
    raw = "Price\u2014\u201cok\u201d \u2013 end"
    out = preprocess_text(raw)
    assert "\u2014" not in out
    assert '"' in out


def test_preprocess_collapses_spaces():
    assert preprocess_text("a    b\t\tc") == "a b c"
