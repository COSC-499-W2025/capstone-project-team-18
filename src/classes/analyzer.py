"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""
from .report import FileReport
from .statistic import Statistic, StatisticIndex, FileStatCollection, FileDomain
import datetime
from pathlib import Path
import logging
import re
from typing import Optional
import ast
from utils.project_discovery import ProjectFiles
from charset_normalizer import from_path

logger = logging.basicConfig(level=logging.DEBUG)


def extract_file_reports(project_file: Optional[ProjectFiles]) -> Optional[list[FileReport]]:
    """
    Method to extract inidvidual fileReports within each project
    """

    if project_file is None:
        return None

    # Given a single project for a user and the project's structure return a list with each fileReport
    projectFiles = project_file.file_paths

    # list of reports for each file in an individual project to be returned
    reports = []
    for file in projectFiles:
        analyzer = BaseFileAnalyzer(project_file.root_path + "/" + file)
        reports.append(analyzer.analyze())

    return reports


class BaseFileAnalyzer:
    """
    Base class for file analysis. Provides a framework for collecting
    file-level statistics.

    To analyze a specific file, extend this class and implement the
    _process method. In this method, call the _process method of the
    superclass to collect basic statistics, then add any file-specific
    statistics to the StatisticIndex (self.stats).
    to the StatisticIndex (self.stats).

    Attributes:
        filepath (str): The path to the file being analyzed.
        stats (StatisticIndex): The index holding collected statistics.

    Statistics:
        - DATE_CREATED
        - DATE_ACCESSED
        - DATE_MODIFIED
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.stats = StatisticIndex()

    def _process(self) -> None:
        """
        A private function that collects basic statistics available for any file.
        This includes a file's:
        - Creation date
        - Last modified/accessed date
        - Size (in bytes)

        All of the metadata is wrapped into a list and put into `self.stats`.
        """
        try:
            metadata = Path(self.filepath).stat()

            # Map file statistic templates to their corresponding timestamp values
            timestamps = {
                FileStatCollection.DATE_CREATED.value: getattr(metadata, "st_birthtime", metadata.st_ctime),
                FileStatCollection.DATE_ACCESSED.value: metadata.st_atime,
                FileStatCollection.DATE_MODIFIED.value: metadata.st_mtime,
            }

            # Add timestamp stats
            for template, value in timestamps.items():
                self.stats.add(
                    Statistic(template, datetime.datetime.fromtimestamp(value)))

            self.stats.add(
                Statistic(FileStatCollection.FILE_SIZE_BYTES.value, metadata.st_size))

        except (FileNotFoundError, PermissionError, OSError, AttributeError) as e:
            logging.error(
                f"Couldn't access metadata for a file in: {self.filepath}. \nError thrown: {str(e)}")

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, filepath=self.filepath)

    def extract_file_reports(self, project_title: str, project_structure: dict) -> list:
        """
        Method to extract individual fileReports within each project
        """
        # Given a single project for a user and the project's structure return a list with each fileReport
        projectFiles = project_structure.get(project_title)
        # list of reports for each file in an individual project to be returned
        reports = []
        if projectFiles is not None:
            for file in projectFiles:
                analyzer = BaseFileAnalyzer(file)
                reports.append(analyzer.analyze())
        else:
            return None
        return reports


class TextFileAnalyzer(BaseFileAnalyzer):
    """
    Analyzer for text-based files. Extends BaseFileAnalyzer.

    This class will parse a file that contains text and log the
    raw line count, but more specific type of stats are given
    to the sublcasses which are: CodeFileAnalyzer and
    NaturalLanguageAnalyzer.

    Attributes:
        text_context : str The string repersentation of
        the text in the file

    Statistics:
        - LINES_IN_FILE
    """

    def __init__(self, filepath: str):
        super().__init__(filepath)

        # Open the file and use the charset_normalizer package to automatically
        # detect the file's encoding
        try:
            self.text_content = str(from_path(self.filepath).best())
        except Exception as e:
            logging.debug(
                f"{self.__class__} tried to open {self.filepath} but got error {e}")
            raise

    def _process(self) -> None:
        super()._process()

        lines_broken = self.text_content.split("\n")

        stats = [
            Statistic(FileStatCollection.LINES_IN_FILE.value,
                      len(lines_broken)),
        ]

        self.stats.extend(stats)


class NaturalLanguageAnalyzer(TextFileAnalyzer):
    """
    This analyzer is for files that contain natural
    text (.docx, .md, .txt).

    Statistics:
        - WORD_COUNT
        - CHARACTER_COUNT
        - SENTENCE_COUNT
        - ARI_WRITING_SCORE
        - TYPE_OF_FILE
    """

    def _process(self) -> None:
        super()._process()

        words = re.findall(r"\b\w+(?:'\w+)?\b", self.text_content)

        word_count = len(words)
        character_count = len(re.findall(r"[A-Za-z0-9]", self.text_content))

        # A key assumption here is that sentences end with ., !, or ? characters.
        # Often times in documentation, sentences may not end with proper punctuation,
        # so we use a more lenient definition for sentence boundaries.
        sentence_count = len(re.findall(r"[.!?]+", self.text_content))

        stats = [
            Statistic(FileStatCollection.TYPE_OF_FILE.value,
                      FileDomain.DOCUMENTATION),
            Statistic(FileStatCollection.WORD_COUNT.value,
                      word_count),
            Statistic(FileStatCollection.CHARACTER_COUNT.value,
                      character_count),
            Statistic(FileStatCollection.SENTENCE_COUNT.value,
                      sentence_count),
            Statistic(FileStatCollection.ARI_WRITING_SCORE.value,
                      self._ari_score(character_count, word_count, sentence_count))
        ]

        self.stats.extend(stats)

    def _ari_score(self, character_count: int, word_count: int, sentence_count: int) -> float:
        """
        Calculates the Automated readability index (ARI) readability
        score for English text. The output is the US grade level
        that is needed to read this text (e.g. 6.7 would be about
        a 7th grade level). Formula is defined here:

        https://en.wikipedia.org/wiki/Automated_readability_index
        """
        # Handle edge cases to prevent division by zero
        if word_count == 0 or sentence_count == 0:
            return 0.0

    
        
        return 4.71 * (character_count / word_count) + 0.5 * (word_count / sentence_count) - 21.43


class CodeFileAnalyzer(TextFileAnalyzer):
    """
    This analyzer is for files that contain source code
    (.py, .js, .java, etc).

    Statistics:
        - TYPE_OF_FILE
    """

    def _process(self) -> None:
        super()._process()

        stats = [
            Statistic(FileStatCollection.TYPE_OF_FILE.value,
                      FileDomain.CODE)
        ]

        self.stats.extend(stats)


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


class TypeScriptAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for TypeScript source code files (.ts).

    Statistics:
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - NUMBER_OF_INTERFACES
        - IMPORTED_PACKAGES
    """

    def _process(self) -> None:
        super()._process()

        # Classes
        class_count = len(re.findall(r'\bclass\s+(\w+)', self.text_content))

        # Interfaces
        interface_count = len(re.findall(
            r'\binterface\s+(\w+)', self.text_content))

        # Functions (named, arrow, and exported)
        # Avoid double-counting exported functions
        named_funcs = set(re.findall(
            r'\bfunction\s+(\w+)\s*\(', self.text_content))
        arrow_funcs = set(re.findall(
            r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[\w]+)\s*=>', self.text_content))
        exported_funcs = set(re.findall(
            r'export\s+function\s+(\w+)\s*\(', self.text_content))
        function_count = len(named_funcs | arrow_funcs | exported_funcs)

        # Imports
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
            Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value,
                      interface_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      package_imports),
        ]

        self.stats.extend(stats)

class CSSAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for CSS files (.css).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (treated as number of rule blocks)
        - NUMBER_OF_CLASSES    (distinct `.class` selectors)
        - IMPORTED_PACKAGES    (@import targets)
    """
    def _process(self) -> None:
        super()._process()

        # Rule blocks like `selector { ... }` (skip leading @ that aren't blocks)
        rule_blocks = re.findall(r'[^@{}][^{]+\{[^}]*\}', self.text_content, re.DOTALL)
        rule_count = len(rule_blocks)

        # Distinct .class selectors
        class_selectors = set(re.findall(r'\.([a-zA-Z_-][\w-]*)', self.text_content))

        # @import url(...) or "..."
        imports = re.findall(
            r'@import\s+(?:url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)|[\'"]([^\'"]+)[\'"])',
            self.text_content
        )
        imported_packages = [a or b for a, b in imports]

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, rule_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, len(class_selectors)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value, imported_packages),
        ]
        self.stats.extend(stats)

class HTMLAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for HTML files (.html, .htm).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (treated as number of <script> blocks)
        - NUMBER_OF_CLASSES    (distinct class tokens)
        - IMPORTED_PACKAGES    (external resources: script/src, link/href, img/src)
    """
    def _process(self) -> None:
        super()._process()

        # Count <script> blocks
        script_blocks = re.findall(r'<\s*script\b', self.text_content, re.IGNORECASE)
        script_count = len(script_blocks)

        # Distinct class tokens from class="a b c"
        class_attrs = re.findall(
            r'class\s*=\s*"(.*?)"|class\s*=\s*\'(.*?)\'',
            self.text_content,
            re.IGNORECASE | re.DOTALL
        )
        class_tokens = set()
        for a, b in class_attrs:
            raw = a or b or ""
            for tok in re.split(r'\s+', raw.strip()):
                if tok:
                    class_tokens.add(tok)

        # External resources
        srcs = re.findall(r'<\s*script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', self.text_content, re.IGNORECASE)
        links = re.findall(r'<\s*link[^>]*\bhref\s*=\s*["\']([^"\']+)["\']', self.text_content, re.IGNORECASE)
        imgs = re.findall(r'<\s*img[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', self.text_content, re.IGNORECASE)
        imported_packages = list(set(srcs + links + imgs))

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, script_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value, imported_packages),
        ]
        self.stats.extend(stats)

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

        func_def_names = set(re.findall(r'\bfunction\s+([a-zA-Z_]\w*)\s*\(', self.text_content))
        short_arrow_defs = re.findall(r'\bfn\s*\(', self.text_content)  # anonymous short functions
        function_count = len(func_def_names) + len(short_arrow_defs)

        class_count = len(re.findall(r'\bclass\s+[A-Za-z_]\w*', self.text_content))
        interface_count = len(re.findall(r'\binterface\s+[A-Za-z_]\w*', self.text_content))

        namespace_imports = re.findall(r'\buse\s+([A-Za-z_][\w\\]+)\s*;', self.text_content)
        includes = re.findall(
            r'\b(?:require|include|require_once|include_once)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            self.text_content
        )
        imported_packages = list(set(namespace_imports + includes))

        stats = [
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, class_count),
            Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value, interface_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value, imported_packages),
        ]
        self.stats.extend(stats)


def get_appropriate_analyzer(filepath: str) -> BaseFileAnalyzer:
    """
    Factory function to return the most appropriate analyzer for a given file.
    This allows FileReport to automatically use the best analyzer.
    """

    file_path = Path(filepath)
    extension = file_path.suffix.lower()

    # Natural language files
    natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
    if extension in natural_language_extensions:
        return NaturalLanguageAnalyzer(filepath)

    # Python files
    if extension == '.py':
        return PythonAnalyzer(filepath)

    # Java files
    if extension == '.java':
        return JavaAnalyzer(filepath)

    # JavaScript files
    if extension in {'.js', '.jsx'}:
        return JavaScriptAnalyzer(filepath)

    # C files
    if extension == '.c':
        return CAnalyzer(filepath)

    # TypeScript files
    if extension in {'.ts', '.tsx'}:
        return TypeScriptAnalyzer(filepath)
    
    if extension == '.css':
        return CSSAnalyzer(filepath)
    
    if extension in {'.html', '.htm'}:
        return HTMLAnalyzer(filepath)
    
    if extension == '.php':
        return PHPAnalyzer(filepath)

    # Text-based files
    text_extensions = {'.xml', '.json', '.yml', '.yaml'}
    if extension in text_extensions:
        return TextFileAnalyzer(filepath)

    # Default to base analyzer
    return BaseFileAnalyzer(filepath)

