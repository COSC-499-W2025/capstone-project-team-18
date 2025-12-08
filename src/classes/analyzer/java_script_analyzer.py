import re
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JavaScriptAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for JavaScript source code files (.js).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - IMPORTED_PACKAGES
    """

    def _process(self) -> None:
        super()._process()

        class_count = len(re.findall(r'\bclass\s+(\w+)', self.text_content))

        function_count = (
            len(re.findall(r'\bfunction\s+(\w+)\s*\(', self.text_content)) +
            len(re.findall(r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>', self.text_content)) +
            len(re.findall(
                r'\b(?:const|let|var)\s+(\w+)\s*=\s*function\s*\(', self.text_content))
        )

        all_imports = (
            re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', self.text_content) +
            re.findall(
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', self.text_content)
        )
        package_imports = list(set(
            imp.split('/')[0] for imp in all_imports
            if not imp.startswith('.') and not imp.startswith('/')
        ))

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, class_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      package_imports),
        ]

        self.stats.extend(stats)
