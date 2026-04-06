import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.core.statistic import Statistic, FileStatCollection
from src.core.analyzer.specific_code_analyzer import SpecificCodeAnalyzer
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


_FONT_HOSTNAMES = {
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "use.typekit.net",
    "use.fontawesome.com",
    "kit.fontawesome.com",
}


def _is_external(url: str) -> bool:
    """Return True if the URL points to an external (CDN/remote) resource."""
    return url.startswith("http://") or url.startswith("https://") or url.startswith("//")


def _is_font_url(url: str) -> bool:
    """Return True if the URL serves fonts rather than a JS/CSS framework."""
    try:
        full_url = url if url.startswith("http") else f"https:{url}"
        hostname = urlparse(full_url).hostname or ""
        return hostname in _FONT_HOSTNAMES
    except Exception:
        return False


def _extract_library_name(url: str) -> str:
    """Extract a clean library name from a CDN URL, falling back to the raw URL."""
    try:
        full_url = url if url.startswith("http") else f"https:{url}"
        parsed = urlparse(full_url)
        hostname = parsed.hostname or ""
        path = parsed.path

        # jsdelivr.net/npm/PACKAGE@version/...
        if "jsdelivr.net" in hostname:
            m = re.search(r"/(?:npm|gh)/([^/@]+)", path)
            if m:
                return m.group(1)

        # cdnjs.cloudflare.com/ajax/libs/PACKAGE/version/...
        if "cdnjs.cloudflare.com" in hostname:
            m = re.search(r"/ajax/libs/([^/]+)", path)
            if m:
                return m.group(1)

        # unpkg.com/PACKAGE@version/...
        if "unpkg.com" in hostname:
            m = re.search(r"/([^/@]+)", path)
            if m:
                return m.group(1)

        # googleapis.com/ajax/libs/PACKAGE/version/...
        if "googleapis.com" in hostname:
            m = re.search(r"/ajax/libs/([^/]+)", path)
            if m:
                return m.group(1)

        # Fall back: strip version and extension from the filename
        filename = path.rstrip("/").split("/")[-1]
        name = re.sub(r"(\.min)?\.(js|css)$", "", filename)
        name = re.sub(r"[-.]?\d+(\.\d+)*$", "", name)
        return name if name else url

    except Exception:
        return url


class HTMLAnalyzer(SpecificCodeAnalyzer):
    """
    Analyzer for HTML files (.html, .htm).

    Statistics:
        - NUMBER_OF_FUNCTIONS  (count of <script> blocks, inline + external)
        - NUMBER_OF_CLASSES    (distinct class tokens across elements)
        - IMPORTED_PACKAGES    (CDN-hosted libraries only: <script src>, <link rel="stylesheet" href>)
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

        # CDN-hosted scripts only (no fonts)
        script_libs = [
            _extract_library_name(s["src"])
            for s in soup.find_all("script", src=True)
            if _is_external(s["src"]) and not _is_font_url(s["src"])
        ]

        # CDN-hosted stylesheets only (rel="stylesheet", no fonts)
        stylesheet_libs = [
            _extract_library_name(l["href"])
            for l in soup.find_all("link", rel="stylesheet", href=True)
            if _is_external(l["href"]) and not _is_font_url(l["href"])
        ]

        imported_packages = list(dict.fromkeys(script_libs + stylesheet_libs))

        self.stats.extend([
            Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, script_count),
            Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, len(class_tokens)),
            Statistic(FileStatCollection.IMPORTED_PACKAGES.value, imported_packages),
        ])
