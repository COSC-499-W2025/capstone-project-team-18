import re
import tinycss2
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSSAnalyzer(CodeFileAnalyzer):
    """
    Analyzer for CSS source files (.css).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (rule blocks: style rules + at-rules with blocks)
        - NUMBER_OF_CLASSES    (distinct `.class` selectors)
        - IMPORTED_PACKAGES    (@import targets)

    Note:
        `NUMBER_OF_FUNCTIONS` counts top-level style rules and at-rules that have a block.
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
