from bs4 import BeautifulSoup

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.specific_code_analyzer import SpecificCodeAnalyzer
from src.utils.log.logging import get_logger

logger = get_logger(__name__)


class HTMLAnalyzer(SpecificCodeAnalyzer):
    """
    Analyzer for HTML files (.html, .htm).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (count of <script> blocks, inline + external)
        - NUMBER_OF_CLASSES    (distinct class tokens across elements)
        - IMPORTED_PACKAGES    (external resources: <script src>, <link href>, <img src>)
        - NUMBER_OF_FUNCTIONS
        - NUMBER_OF_CLASSES
        - IMPORTED_PACKAGES
    """

    def _process_not_empty(self) -> None:

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
