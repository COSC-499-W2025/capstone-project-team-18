import re
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for C source code files (.c).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES (used for structs)
        - IMPORTED_PACKAGES (used for #includes)
    """

    def _process(self) -> None:
        super()._process()

        # Function definitions (improved heuristic: match return type, name, params, and opening brace)
        function_count = len(re.findall(
            r'^[\w\s\*]+\s+([a-zA-Z_][\w]*)\s*\([^)]*\)\s*\{', self.text_content, re.MULTILINE))

        # Struct definitions (match 'struct Name { ... };') - treating structs as classes
        struct_count = len(re.findall(
            r'struct\s+[a-zA-Z_][\w]*\s*\{[^}]*\}\s*;', self.text_content, re.DOTALL))

        # Includes - extract header names for IMPORTED_PACKAGES
        included_headers = re.findall(
            r'^\s*#include\s+[<"]([^>"]+)[>"]', self.text_content, re.MULTILINE)

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, struct_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      included_headers),
        ]

        self.stats.extend(stats)
