import re
import logging

from src.classes.statistic import Statistic, FileStatCollection, FileDomain
from src.classes.analyzer.text_file_analyzer import TextFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NaturalLanguageAnalyzer(TextFileAnalyzer):
    """
    This analyzer is for files that contain natural
    text (.docx, .md, .txt).

    Statistics:
        - WORD_COUNT
        - CHARACTER_COUNT
        - SENTENCE_COUNT
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
                      sentence_count)
        ]

        self.stats.extend(stats)
