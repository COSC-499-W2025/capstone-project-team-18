import logging
import ast

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PythonAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for Python source code files (.py).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - IMPORTED_PACKAGES
    """

    # TODO: IMPORTED_PACKAGES right now looks at all imports, but
    # we should filter out standard library imports vs 3rd party
    # vs local imports. Maybe this needs to be done at the project
    # level though.

    def _process(self) -> None:
        super()._process()

        # We parse the Python code using the ast module to
        # extract statistics.
        try:
            tree = ast.parse(self.text_content)
        except SyntaxError as e:
            logging.error(f"Syntax error while parsing {self.filepath}: {e}")
            return

        function_count = 0
        class_count = 0
        package_imports = []

        # For every node in the AST, check if it's a function or class definition
        # or an import statement. For imports, we just grab the top-level package name
        # and disregarding any relative imports.
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    package_imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    package_imports.append(node.module.split('.')[0])

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value,
                      class_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      list(set(package_imports))),
        ]

        self.stats.extend(stats)
