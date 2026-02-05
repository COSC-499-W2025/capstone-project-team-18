"""
Tests for NaturalLanguageAnalyzer.
"""

from src.core.ML.models.readme_analysis import (keyphrase_extraction,
                                                readme_insights)
from src.core.statistic import FileDomain, FileStatCollection


def _readme_report(tmp_path, create_temp_file, monkeypatch, filename, content, get_ready_specific_analyzer):
    def fake_extract(text, top_n):
        return ["REST API"] if "REST" in text else ["Key Phrase"]

    # Stub model calls so tests are fast and do not download large models.
    monkeypatch.setattr(
        keyphrase_extraction, "_extract_with_keybert", fake_extract)

    def _fake_classifier(_text, _labels, multi_label=False):
        return {"labels": ["Professional"], "scores": [0.99]}

    monkeypatch.setattr(readme_insights, "_get_classifier",
                        lambda: _fake_classifier)
    root, name = create_temp_file(filename, content, tmp_path)
    return get_ready_specific_analyzer(root, name).analyze()


def test_NaturalLanguageAnalyzer_core_stats(tmp_path, create_temp_file, get_ready_specific_analyzer):
    content = (
        "# Welcome"
        "\n"
        "## Introduction"
        "\n"
        "Hello, welcome to my test of the NaturalLanguageAnalyzer. I have "
        "personally verified all the stats we are going to be testing for. "
        "This means that if the test gets something wrong, it is because some "
        "logic with the counting is wrong! Don't you love python testing? Here are "
        "some new lines to try to mess with the class."
        "\n"
        "## More Text \n"
        "Now I want to throw in another sentence!\n"
        "Here is a list of things:\n"
        "   - Yellow\n"
        "   - Red\n"
        "   - Green\n"
        "   - 1 Fish 2 Fish\n"
    )

    root, name = create_temp_file(
        "test_NaturalLanguageAnalyzer_core_stats.md", content, tmp_path)
    report = get_ready_specific_analyzer(root, name).analyze()

    REAL_WORD_COUNT = 83
    REAL_ALPHA_NUMERIC_CHARACTER_COUNT = 356
    REAL_SENTENCE_COUNT = 6
    REAL_TYPE_OF_FILE = FileDomain.DOCUMENTATION

    measured_word_count = report.get_value(FileStatCollection.WORD_COUNT.value)
    measured_character_count = report.get_value(
        FileStatCollection.CHARACTER_COUNT.value)
    measured_sentence_count = report.get_value(
        FileStatCollection.SENTENCE_COUNT.value)
    measured_type_of_file = report.get_value(
        FileStatCollection.TYPE_OF_FILE.value)

    assert REAL_WORD_COUNT == measured_word_count
    assert REAL_ALPHA_NUMERIC_CHARACTER_COUNT == measured_character_count
    assert REAL_SENTENCE_COUNT == measured_sentence_count
    assert REAL_TYPE_OF_FILE == measured_type_of_file


def test_create_with_analysis_natural_language_md(tmp_path, create_temp_file, get_ready_specific_analyzer):
    """Test natural language analysis for Markdown files."""
    content = (
        "# Test Document\n\n"
        "This is a test document with multiple sentences. "
        "It contains exactly fifty words in total to test our word counting functionality accurately. "
        "The document also tests sentence counting and character analysis for the automated readability index calculation.\n\n"
        "## Section Two\n"
        "Another paragraph for testing purposes."
    )

    root, name = create_temp_file("test.md", content, tmp_path)
    analyzer = get_ready_specific_analyzer(root, name)
    file_report = analyzer.analyze()

    # Test that natural language statistics are present
    assert file_report.get_value(
        FileStatCollection.WORD_COUNT.value) is not None
    assert file_report.get_value(
        FileStatCollection.CHARACTER_COUNT.value) is not None
    assert file_report.get_value(
        FileStatCollection.SENTENCE_COUNT.value) is not None

    # Test file type is correctly identified
    file_type = file_report.get_value(FileStatCollection.TYPE_OF_FILE.value)
    assert file_type == FileDomain.DOCUMENTATION

    # Test basic file statistics are also present
    assert file_report.get_value(
        FileStatCollection.FILE_SIZE_BYTES.value) is not None
    assert file_report.get_value(
        FileStatCollection.DATE_CREATED.value) is not None


def test_natural_language_file_with_only_words(tmp_path, create_temp_file, get_ready_specific_analyzer):
    """Test natural language analysis with words but no sentence punctuation."""
    content = "just some words without any punctuation marks"

    root, name = create_temp_file("words_only.md", content, tmp_path)
    analyzer = get_ready_specific_analyzer(root, name)
    file_report = analyzer.analyze()

    # Should not crash due to division by zero protection
    word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
    sentence_count = file_report.get_value(
        FileStatCollection.SENTENCE_COUNT.value)

    assert word_count > 0
    assert sentence_count == 0  # No punctuation


def test_natural_language_statistics_comprehensive(tmp_path, create_temp_file, get_ready_specific_analyzer):
    """Test comprehensive natural language statistics measurement."""
    content = (
        "This is a comprehensive test document. "
        "It contains multiple sentences for testing! "
        "Does it work correctly with questions? "
        "Let's find out with this detailed analysis.\n\n"
        "Here's another paragraph with technical content. "
        "The automated readability index should be calculated properly."
    )

    create_temp_file("comprehensive.md", content, tmp_path)
    analyzer = get_ready_specific_analyzer(str(tmp_path), "comprehensive.md")
    file_report = analyzer.analyze()

    # Test all natural language statistics are present and reasonable
    word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
    char_count = file_report.get_value(
        FileStatCollection.CHARACTER_COUNT.value)
    sentence_count = file_report.get_value(
        FileStatCollection.SENTENCE_COUNT.value)

    assert isinstance(word_count, int)
    assert word_count > 0

    assert isinstance(char_count, int)
    assert char_count > 0

    assert isinstance(sentence_count, int)
    assert sentence_count > 0


def test_readme_keyphrase_extraction(tmp_path, create_temp_file, monkeypatch, get_ready_specific_analyzer):
    report = _readme_report(
        tmp_path,
        create_temp_file,
        monkeypatch,
        "README.md",
        "# Project X\nA REST API built with FastAPI and PostgreSQL. "
        "Includes OAuth authentication and Docker deployment.",
        get_ready_specific_analyzer
    )
    keyphrases = report.get_value(FileStatCollection.README_KEYPHRASES.value)
    tone = report.get_value(FileStatCollection.README_TONE.value)
    assert isinstance(keyphrases, list)
    assert len(keyphrases) > 0
    assert tone == "Professional"
    assert tone == "Professional"
