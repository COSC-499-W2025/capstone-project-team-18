"""
This file holds all the Analyzer classes. These are classes will analyze
a file and generate a report with statistics.
"""
import os
import time
from .report import FileReport
from .statistic import Statistic, StatisticIndex, FileStatCollection, FileDomain, CodingLanguage, FileStatisticTemplate
import datetime
from pathlib import Path
import logging
import re
from typing import Optional, Any
import ast
from src.utils.project_discovery import ProjectFiles
from charset_normalizer import from_path
from git import GitCommandError, Repo, InvalidGitRepositoryError
import tinycss2
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_file_reports(project_file: Optional[ProjectFiles], email: Optional[str] = None) -> Optional[list[FileReport]]:
    """
    Method to extract individual fileReports within each project
    """

    if project_file is None:
        return None

    # Given a single project for a user and the project's structure return a list with each fileReport
    projectFiles = project_file.file_paths

    # list of reports for each file in an individual project to be returned
    reports = []
    for file in projectFiles:

        analyzer = get_appropriate_analyzer(
            project_file.root_path, file, project_file.repo, email)

        if analyzer.should_inculde() is False:
            continue

        try:
            reports.append(analyzer.analyze())
        except Exception as e:
            logger.error(
                f"Error analyzing file {file} in {project_file.name}: {e}")

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
        realtive_path (str): The path to the file relative to the
            top-level project directory.
        repo (Optional[Repo]): The Git repository object if the file
            is part of a Git repository.
        email (Optional[str]): The email of the user analyzing the file.

    Statistics:
        - DATE_CREATED
        - DATE_MODIFIED
        - FILE_SIZE_BYTES
    """

    def __init__(self,
                 path_to_top_level_project: str,
                 relative_path: str,
                 repo: Optional[Repo] = None,
                 email: Optional[str] = None
                 ):

        self.path_to_top_level_project = path_to_top_level_project
        self.relative_path = relative_path
        self.filepath = f"{path_to_top_level_project}/{relative_path}"
        self.repo = repo
        self.email = email
        self.stats = StatisticIndex()
        self.blame_info = None
        self.is_git_tracked = self.file_in_git_repo()

    def file_in_git_repo(self) -> bool:
        """
        Check to see the project is in a git repository and
        if so, that this specific file is tracked by git.
        """

        if self.repo is None:
            return False

        try:
            self.blame_info = self.repo.blame('HEAD', self.relative_path)

            return True
        except (ValueError, GitCommandError, Exception) as e:
            logger.debug(
                f"File not tracked by git or git error: {e}")
            return False

    def should_inculde(self) -> bool:
        """
        This is a lightweight check to see if the file should be
        included in analysis. By deafult, all files are included.

        A file is excluded if it meets certain criteria:
            - If the user has configured to exclude files of this type
            - If user has given their email, and the file is tracked by git,
                but none of the lines in the file were authored by the user.

        Returns:
            bool: True if the file should be included, False otherwise.
        """

        # TODO : Implement user preferences for excluding certain file types

        if not self.is_git_tracked or not self.email or not self.repo:
            return True

        if self.blame_info is None:
            return True

        # Use the git command "shortlog" to see if a user has contributed to a file.
        git_cmd = self.repo.git
        short_log = git_cmd.shortlog(
            "-s", "-n", "--email", "HEAD", "--", self.relative_path)

        if self.email in short_log:
            return True

        return False

    def _process(self) -> None:
        """
        This is the main processing function for the analyzers family
        of classes. It will always be run first before any subclass
        analysis is done.

        Here we collect basic file statistics that are
        common to all file types. That being:
        - Creation date
        - Last modified date
        - Size (in bytes)

        If the file is part of a Git repository, we get the creation
        and last modified dates from the Git commit history. If not,
        we fall back to the filesystem metadata.

        Likewise with any of the analyzers that extend this class,
        you can call this _process method and know that these basic
        statistics will be collected in the self.stats StatisticIndex.

        """

        metadata = None
        metadata = Path(self.filepath).stat()

        stats = [
            Statistic(FileStatCollection.FILE_SIZE_BYTES.value,
                      metadata.st_size),
        ]

        if self.is_git_tracked:
            # Get the creation date from the first commit
            # and get the last modified date from the latest commit

            try:
                commits = list(self.repo.iter_commits(  # pyright: ignore[reportOptionalMemberAccess]
                    paths=self.relative_path))
            except Exception as e:
                logger.debug(f"InvalidGitRepositoryError: {e}")
                commits = []

            if commits:
                first_commit = commits[-1]
                latest_commit = commits[0]

                stats.append(Statistic(FileStatCollection.DATE_CREATED.value, datetime.datetime.fromtimestamp(
                    first_commit.authored_date)))
                stats.append(Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime.fromtimestamp(
                    latest_commit.authored_date)))
        else:
            # Fallback to filesystem metadata

            """
            Special note here:

            Linux corrupts the st_birthtime to be the time that
            the file was unzipped.
            Linux's date access actually contains the true birthtime so
            we treat that as DATE_CREATED
            """

            stats.append(Statistic(FileStatCollection.DATE_CREATED.value, datetime.datetime.fromtimestamp(
                metadata.st_atime)))
            stats.append(Statistic(FileStatCollection.DATE_MODIFIED.value, datetime.datetime.fromtimestamp(
                metadata.st_mtime)))

        self.stats.extend(stats)

    def analyze(self) -> FileReport:
        """
        Analyze the file and return a FileReport with collected statistics.
        """
        self._process()

        return FileReport(statistics=self.stats, filepath=self.relative_path)


class TextFileAnalyzer(BaseFileAnalyzer):
    """
    Analyzer for text-based files. Extends BaseFileAnalyzer.

    This class will parse a file that contains text and log the
    raw line count, but more specific type of stats are given
    to the subclasses which are: CodeFileAnalyzer and
    NaturalLanguageAnalyzer.

    Attributes:
        text_context : str The string representation of
        the text in the file

    Statistics:
        - LINES_IN_FILE
    """

    def _process(self) -> None:
        super()._process()

        # Open the file and use the charset_normalizer package to automatically
        # detect the file's encoding
        try:
            self.text_content = str(from_path(self.filepath).best())
        except Exception as e:
            logging.debug(
                f"{self.__class__} tried to open {self.filepath} but got error {e}")
            raise

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
        - PERCENTAGE_LINES_COMMITTED
    """

    def _process(self) -> None:
        super()._process()

        file_commit_percentage = self._get_file_commit_percentage()

        if file_commit_percentage is not None:
            self.stats.add(Statistic(FileStatCollection.PERCENTAGE_LINES_COMMITTED.value,
                                     file_commit_percentage))

        self._determine_file_domain()
        self._find_coding_language()

    def _determine_file_domain(self) -> None:
        """
        Checks to see if the code is a test file or rather
        just a plain code file.

        It checks the filename and directory and looks for
        the test keyword
        """

        fd = FileDomain.CODE

        path = Path(self.filepath)
        name = path.name.lower()

        if name.startswith("test_") or "_test" in name:
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

    def _get_file_commit_percentage(self) -> Optional[float]:
        """
        Calculate the percentage of lines in the file
        that were authored by the user with the given email.
        """

        # If the file is not tracked by git or email is None, return None
        if self.is_git_tracked is False or self.email is None or self.repo is None:
            return None

        try:
            # gets blame for each line
            blame_info = self.repo.blame('HEAD', self.relative_path)

            commit_count = 0
            line_count = 0
            for commit, lines in blame_info:
                line_count += len(lines)
                if commit.author.email == self.email:
                    commit_count += len(lines)

            if line_count == 0:
                return 0.0

            return round((commit_count / line_count) * 100, 2)
        except InvalidGitRepositoryError as e:
            logger.debug(f"InvalidGitRepositoryError: {e}")
            return None
        except Exception as e:
            logger.debug(f"Exception while computing commit percentage: {e}")
            return None


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
    Analyzer for CSS source files (.css).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (rule blocks: style rules + at-rules with blocks)
        - NUMBER_OF_CLASSES    (distinct `.class` selectors)
        - IMPORTED_PACKAGES    (@import targets)

    Note:
        NUMBER_OF_FUNCTIONS counts top-level style rules and at-rules that have a block.
        Nested qualified rules inside at-rules (e.g., selectors within @media) are **not**
        counted separately.
    """

    def _process(self) -> None:
        super()._process()

        # Empty file: emit zero/empty stats so keys always exist
        if not self.text_content.strip():
            logger.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            logger.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            self.stats.extend([
                Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, 0),
                Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, 0),
                Statistic(FileStatCollection.IMPORTED_PACKAGES.value, []),
            ])
            return

        if tinycss2 is not None:
            rules = tinycss2.parse_stylesheet(
                self.text_content,
                skip_comments=True,
                skip_whitespace=True,
            )

            rule_count = 0
            class_tokens: set[str] = set()
            imports: list[str] = []

            def extract_classes_from_prelude(prelude) -> list[str]:
                selector_text = tinycss2.serialize(prelude or [])
                return re.findall(r'\.([a-zA-Z_-][\w-]*)', selector_text)

            def extract_imports_from_prelude(prelude) -> list[str]:
                found: list[str] = []
                for t in (prelude or []):
                    if t.type == "string":
                        found.append(t.value)
                    elif t.type == "url":
                        found.append(t.value)
                    elif t.type == "function" and getattr(t, "name", "").lower() == "url":
                        for a in (t.arguments or []):
                            if a.type == "string":
                                found.append(a.value)
                return found

            for r in rules:
                if r.type == "at-rule":
                    at_kw = (r.at_keyword or "").lower()

                    if at_kw == "import":
                        imports.extend(extract_imports_from_prelude(r.prelude))

                    # Count at-rule blocks and inspect nested qualified rules
                    if r.content is not None:
                        rule_count += 1
                        nested_rules = tinycss2.parse_rule_list(r.content)
                        for nr in nested_rules:
                            if nr.type == "qualified-rule":
                                class_tokens.update(
                                    extract_classes_from_prelude(nr.prelude))
                                class_tokens.update(
                                    extract_classes_from_prelude(nr.prelude))

                elif r.type == "qualified-rule":
                    rule_count += 1
                    class_tokens.update(
                        extract_classes_from_prelude(r.prelude))
                    class_tokens.update(
                        extract_classes_from_prelude(r.prelude))

            imported_packages = list(set(imports))

        else:
            # ---- Regex fallback (keeps analyzer usable if tinycss2 isn't installed) ----
            logger.debug(
                "CSSAnalyzer: tinycss2 not installed; using regex fallback.")
            cleaned = re.sub(r'/\*.*?\*/', '',
                             self.text_content, flags=re.DOTALL)
            logger.debug(
                "CSSAnalyzer: tinycss2 not installed; using regex fallback.")
            cleaned = re.sub(r'/\*.*?\*/', '',
                             self.text_content, flags=re.DOTALL)

            # Count style rules and at-rule blocks (best-effort)
            rule_blocks = re.findall(
                r'[^{@][^{]+\{[^{}]*\}|@[^{}]+\{[^{}]*\}', cleaned)
            rule_blocks = re.findall(
                r'[^{@][^{]+\{[^{}]*\}|@[^{}]+\{[^{}]*\}', cleaned)
            rule_count = len(rule_blocks)

            # Distinct .class selectors (including inside at-rule blocks)
            class_tokens = set(re.findall(r'\.([a-zA-Z_-][\w-]*)', cleaned))

            # Capture @import "x.css" and @import url("x.css")
            imports = re.findall(
                r'@import\s+(?:url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)|[\'"]([^\'"]+)[\'"])',
                cleaned
            )
            imported_packages = list({a or b for a, b in imports})

        self.stats.extend([
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, rule_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value,
                      len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value,
                      len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
        ])


class HTMLAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for HTML files (.html, .htm).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (count of <script> blocks, inline + external)
        - NUMBER_OF_CLASSES    (distinct class tokens across elements)
        - IMPORTED_PACKAGES    (external resources: <script src>, <link href>, <img src>)
    """

    def _process(self) -> None:
        super()._process()

        # Empty file: emit zero/empty stats so keys always exist
        if not self.text_content.strip():
            logger.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            logger.debug(
                f"{self.__class__.__name__}: Empty file {self.filepath}")
            self.stats.extend([
                Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, 0),
                Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, 0),
                Statistic(FileStatCollection.IMPORTED_PACKAGES.value, []),
            ])
            return

        if BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(self.text_content, "lxml")
            except Exception:
                soup = BeautifulSoup(self.text_content, "html.parser")

            # Scripts (inline + external)
            script_count = len(soup.find_all("script"))

            # Distinct class tokens
            class_tokens: set[str] = set()
            for el in soup.find_all(class_=True):
                for c in el.get("class", []):
                    if c:
                        class_tokens.add(c)

            # External resources
            script_srcs = [s["src"] for s in soup.find_all("script", src=True)]
            link_hrefs = [l["href"] for l in soup.find_all("link", href=True)]
            img_srcs = [i["src"] for i in soup.find_all("img", src=True)]
            link_hrefs = [l["href"] for l in soup.find_all("link", href=True)]
            img_srcs = [i["src"] for i in soup.find_all("img", src=True)]
            imported_packages = list({*script_srcs, *link_hrefs, *img_srcs})

        else:
            # ---- Regex fallback (if bs4 isn't installed) ----
            logger.debug(
                "HTMLAnalyzer: BeautifulSoup not installed; using regex fallback.")
            logger.debug(
                "HTMLAnalyzer: BeautifulSoup not installed; using regex fallback.")
            # <script> blocks (inline + external)
            script_count = len(re.findall(
                r'<\s*script\b', self.text_content, re.IGNORECASE))
            script_count = len(re.findall(
                r'<\s*script\b', self.text_content, re.IGNORECASE))

            # class="...", class='...', or class=token
            class_attrs = re.findall(
                r'class\s*=\s*(?:"(.*?)"|\'(.*?)\'|([^\s>]+))',
                self.text_content, re.IGNORECASE | re.DOTALL
            )
            class_tokens: set[str] = set()
            for a, b, c in class_attrs:
                raw = a or b or c or ""
                for tok in re.split(r'\s+', raw.strip()):
                    if tok:
                        class_tokens.add(tok)

            # External resources
            srcs = re.findall(
                r'<\s*script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', self.text_content, re.IGNORECASE)
            links = re.findall(
                r'<\s*link[^>]*\bhref\s*=\s*["\']([^"\']+)["\']',  self.text_content, re.IGNORECASE)
            imgs = re.findall(
                r'<\s*img[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']',    self.text_content, re.IGNORECASE)
            srcs = re.findall(
                r'<\s*script[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', self.text_content, re.IGNORECASE)
            links = re.findall(
                r'<\s*link[^>]*\bhref\s*=\s*["\']([^"\']+)["\']',  self.text_content, re.IGNORECASE)
            imgs = re.findall(
                r'<\s*img[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']',    self.text_content, re.IGNORECASE)
            imported_packages = list(set(srcs + links + imgs))

        self.stats.extend([
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      script_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value,
                      len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      script_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value,
                      len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
        ])


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
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value,
                      function_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, class_count),
            Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value,
                      interface_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
            Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value,
                      interface_count),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value,
                      imported_packages),
        ]
        self.stats.extend(stats)


def get_appropriate_analyzer(
    path_to_top_level_project: str,
    relative_path: str,
    repo: Optional[Repo] = None,
    email: Optional[str] = None
) -> BaseFileAnalyzer:
    """
    Factory function to return the most appropriate analyzer for a given file.
    This allows FileReport to automatically use the best analyzer.
    """

    file_path = Path(path_to_top_level_project + "/" + relative_path)
    extension = file_path.suffix.lower()

    # Natural language files
    natural_language_extensions = {'.md', '.txt', '.rst', '.doc', '.docx'}
    if extension in natural_language_extensions:
        return NaturalLanguageAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # Python files
    if extension == '.py':
        return PythonAnalyzer(path_to_top_level_project, relative_path, repo, email)
    # Java files
    if extension == '.java':
        return JavaAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # JavaScript files
    if extension in {'.js', '.jsx'}:
        return JavaScriptAnalyzer(path_to_top_level_project, relative_path, repo, email)
    # C files
    if extension == '.c':
        return CAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # TypeScript files
    if extension in {'.ts', '.tsx'}:
        return TypeScriptAnalyzer(path_to_top_level_project, relative_path, repo, email)
    # CSS files
    if extension == '.css':
        return CSSAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # HTML or HTM files
    if extension in {'.html', '.htm'}:
        return HTMLAnalyzer(path_to_top_level_project, relative_path, repo, email)
    # PHP files
    if extension == '.php':
        return PHPAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # Text-based files
    text_extensions = {'.xml', '.json', '.yml', '.yaml'}
    if extension in text_extensions:
        return TextFileAnalyzer(path_to_top_level_project, relative_path, repo, email)

    for language in CodingLanguage:
        if extension in language.value[1]:
            return CodeFileAnalyzer(path_to_top_level_project, relative_path, repo, email)

    # Default to base analyzer
    return BaseFileAnalyzer(path_to_top_level_project, relative_path, repo, email)
