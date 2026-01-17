import re

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.specific_code_analyzer import SpecificCodeAnalyzer
from src.utils.log.logging import get_logger

logger = get_logger(__name__)


class JavaAnalyzer(SpecificCodeAnalyzer):
    """
    Analyzer for Java source code files (.java).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - IMPORTED_PACKAGES
    """

    def _process_not_empty(self) -> None:

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
