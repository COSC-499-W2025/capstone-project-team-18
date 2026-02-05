"""
Tests for CodeFileAnalyzer (coding language detection and file domain).
"""
from src.core.analyzer import CodeFileAnalyzer
from src.core.statistic import FileStatCollection, CodingLanguage, FileDomain


def test_determines_correct_coding_language(tmp_path, create_temp_file, get_ready_specific_analyzer):
    file_extensions_to_test = (
        (CodingLanguage.PYTHON, ".py"),
        (CodingLanguage.JAVA, ".java"),
        (CodingLanguage.CSHARP, ".cs"),
        (CodingLanguage.RUBY, ".rb"),
        (CodingLanguage.GO, ".go"),
        (CodingLanguage.TYPESCRIPT, ".ts")
    )

    for value, extension in file_extensions_to_test:
        path = create_temp_file("temp" + extension, "", tmp_path)
        report = get_ready_specific_analyzer(path[0], path[1]).analyze()
        assert report.get_value(
            FileStatCollection.CODING_LANGUAGE.value) == value


def test_unkown_coding_language(tmp_path, create_temp_file, get_ready_specific_analyzer):
    path = create_temp_file("temp" + ".xyx", "", tmp_path)
    report = get_ready_specific_analyzer(path[0], path[1]).analyze()
    assert report.get_value(FileStatCollection.CODING_LANGUAGE.value) is None


def test_file_domain_is_not_test(tmp_path, create_temp_file, get_ready_specific_analyzer):
    filenames = ["intestine_analysis.py",
                 "testsaver.java", "protest_action.ts",
                 "latest_testresults.py", "unit_testdata_loader.py"]

    for filename in filenames:
        file = create_temp_file(
            filename, "print('Hello, world!')", path=tmp_path)
        report = get_ready_specific_analyzer(file[0], file[1]).analyze()

        assert report.get_value(
            FileStatCollection.TYPE_OF_FILE.value) == FileDomain.CODE


def test_file_domain_is_test_by_filename(tmp_path, create_temp_file, get_ready_specific_analyzer):
    filenames = ["test_example.py", "example_test.py", "hello_test_example",
                 "sam_testing.py", "utils.test.py", "api-test-get-requests.js"]

    for filename in filenames:
        file = create_temp_file(
            filename, "print('Hello, world!')", path=tmp_path)
        report = get_ready_specific_analyzer(file[0], file[1]).analyze()

        assert report.get_value(
            FileStatCollection.TYPE_OF_FILE.value) == FileDomain.TEST


def test_file_domain_is_test_by_path(tmp_path, create_temp_file, get_ready_specific_analyzer):
    directory_names = ["tests", "test", "Test"]

    for name in directory_names:
        target_dir = tmp_path / name
        target_dir.mkdir()

        file = create_temp_file("hello_world.py", "", path=target_dir)
        report = get_ready_specific_analyzer(file[0], file[1]).analyze()

        assert report.get_value(
            FileStatCollection.TYPE_OF_FILE.value) == FileDomain.TEST
