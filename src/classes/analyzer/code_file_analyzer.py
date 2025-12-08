import re
from pathlib import Path
import logging

from src.classes.statistic import Statistic, FileStatCollection, FileDomain, CodingLanguage
from src.classes.analyzer.text_file_analyzer import TextFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeFileAnalyzer(TextFileAnalyzer):
    """
    This analyzer is for files that contain source code
    (.py, .js, .java, etc).

    Statistics:
        - TYPE_OF_FILE
        - PERCENTAGE_LINES_COMMITTED
    """

    def _process(self) -> None:
        super()._process()

        self._determine_file_domain()
        self._find_coding_language()

    def _determine_file_domain(self) -> None:
        """
        Checks to see if the code is a test file or rather
        just a plain code file.

        It checks the filename and directory and looks for
        the test keyword
        """

        TEST_FILE_REGEX = re.compile(
            r"(?:^|[\W_])(test|tests|spec|specs|testing)(?:[\W_]|$)", re.IGNORECASE)

        fd = FileDomain.CODE

        path = Path(self.filepath)
        name = path.name.lower()

        if TEST_FILE_REGEX.search(name):
            fd = FileDomain.TEST

        directory_test_keywords = {"test", "tests", "spec"}
        if directory_test_keywords & {p.lower() for p in path.parts}:
            fd = FileDomain.TEST

        self.stats.add(Statistic(FileStatCollection.TYPE_OF_FILE.value, fd))

    def _find_coding_language(self) -> None:
        """
        Find the coding language by file extension.
        We do it here (instead of the sub class analyzers)
        because we can offer support for more languages
        that we do not have analyzers for.

        """
        # Get suffix of file
        suffix = Path(self.filepath).suffix.lower()

        for language in CodingLanguage:
            # Each language.value is a tuple (name, extensions)
            if suffix in language.value[1]:
                return self.stats.add(Statistic(FileStatCollection.CODING_LANGUAGE.value, language))
