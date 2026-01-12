import re
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JavaAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for Java source code files (.java).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - IMPORTED_PACKAGES
    """

    def _process(self) -> None:
        super()._process()

        class_count = len(re.findall(
            r'\b(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*class\s+(\w+)',
            self.text_content))

        function_count = len(re.findall(
            r'\b(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+(?:,\s*\w+)*)?\s*\{',
            self.text_content))

        package_imports = list(set(
            imp.split('.')[0] for imp in re.findall(
                r'^\s*import\s+(?:static\s+)?([a-zA-Z_][\w.]*)',
                self.text_content, re.MULTILINE)))

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, class_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      package_imports),
        ]

        self.stats.extend(stats)
