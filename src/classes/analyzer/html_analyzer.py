import re
from bs4 import BeautifulSoup
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
