import re
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PHPAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for PHP files (.php).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - NUMBER_OF_INTERFACES
        - IMPORTED_PACKAGES  (use/import + include/require targets)
    """

    def _process(self) -> None:
        super()._process()

        if not self.text_content.strip():
            logging.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            logging.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            self.stats.extend([
                Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, 0),
                Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, 0),
                Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value, 0),
                Statistic(FileStatCollection.IMPORTED_PACKAGES.value, []),
            ])
            return

        func_def_names = set(re.findall(
            r'\bfunction\s+([a-zA-Z_]\w*)\s*\(', self.text_content))
        short_arrow_defs = re.findall(r'\bfn\s*\(', self.text_content)
        func_def_names = set(re.findall(
            r'\bfunction\s+([a-zA-Z_]\w*)\s*\(', self.text_content))
        short_arrow_defs = re.findall(r'\bfn\s*\(', self.text_content)
        function_count = len(func_def_names) + len(short_arrow_defs)

        class_count = len(re.findall(
            r'\bclass\s+[A-Za-z_]\w*', self.text_content))
        interface_count = len(re.findall(
            r'\binterface\s+[A-Za-z_]\w*', self.text_content))
        class_count = len(re.findall(
            r'\bclass\s+[A-Za-z_]\w*', self.text_content))
        interface_count = len(re.findall(
            r'\binterface\s+[A-Za-z_]\w*', self.text_content))

        namespace_imports = re.findall(
            r'\buse\s+([A-Za-z_][\w\\]+)\s*;', self.text_content)
        namespace_imports = re.findall(
            r'\buse\s+([A-Za-z_][\w\\]+)\s*;', self.text_content)
        includes = re.findall(
            r'\b(?:require|include|require_once|include_once)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            self.text_content
        )
        imported_packages = list(set(namespace_imports + includes))

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, class_count),
            Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value,
                      interface_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
        ]
        self.stats.extend(stats)
