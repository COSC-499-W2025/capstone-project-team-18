"""
Tests for NaturalLanguageAnalyzer.
"""

from src.classes.analyzer import NaturalLanguageAnalyzer, get_appropriate_analyzer
from src.classes.statistic import FileStatCollection, FileDomain


def test_NaturalLanguageAnalyzer_core_stats(tmp_path, create_temp_file):
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

    file_path = create_temp_file(
        "test_NaturalLanguageAnalyzer_core_stats.md", content, tmp_path)

    report = NaturalLanguageAnalyzer(file_path[0], file_path[1]).analyze()

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


def test_create_with_analysis_natural_language_md(tmp_path, create_temp_file):
    """Test natural language analysis for Markdown files."""
    content = (
        "# Test Document\n\n"
        "This is a test document with multiple sentences. "
        "It contains exactly fifty words in total to test our word counting functionality accurately. "
        "The document also tests sentence counting and character analysis for the automated readability index calculation.\n\n"
        "## Section Two\n"
        "Another paragraph for testing purposes."
    )

    file_path = create_temp_file("test.md", content, tmp_path)

    analyzer = get_appropriate_analyzer(file_path[0], file_path[1])
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


def test_natural_language_file_with_only_words(tmp_path, create_temp_file):
    """Test natural language analysis with words but no sentence punctuation."""
    content = "just some words without any punctuation marks"

    file_path = create_temp_file("words_only.md", content, tmp_path)
    analyzer = get_appropriate_analyzer(file_path[0], file_path[1])
    file_report = analyzer.analyze()

    # Should not crash due to division by zero protection
    word_count = file_report.get_value(FileStatCollection.WORD_COUNT.value)
    sentence_count = file_report.get_value(
        FileStatCollection.SENTENCE_COUNT.value)

    assert word_count > 0
    assert sentence_count == 0  # No punctuation


def test_natural_language_statistics_comprehensive(tmp_path, create_temp_file):
    """Test comprehensive natural language statistics measurement."""
    content = (
        "This is a comprehensive test document. "
        "It contains multiple sentences for testing! "
        "Does it work correctly with questions? "
        "Let's find out with this detailed analysis.\n\n"
        "Here's another paragraph with technical content. "
        "The automated readability index should be calculated properly."
    )

    file_path = create_temp_file("comprehensive.md", content, tmp_path)
    analyzer = get_appropriate_analyzer(str(tmp_path), "comprehensive.md")
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
