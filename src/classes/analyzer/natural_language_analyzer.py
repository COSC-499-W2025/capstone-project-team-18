import re
from pathlib import Path

from src.classes.statistic import Statistic, FileStatCollection, FileDomain
from src.classes.analyzer.text_file_analyzer import TextFileAnalyzer
from src.ML.models.readme_analysis.keyphrase_extraction import extract_readme_keyphrases
from src.ML.models.readme_analysis.readme_insights import classify_readme_tone
from src.utils.log.logging import get_logger

logger = get_logger(__name__)


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

        filename = Path(self.filepath).name.lower()
        if filename.startswith("readme"):
            keyphrases = extract_readme_keyphrases(self.text_content)
            if keyphrases:
                stats.append(
                    Statistic(FileStatCollection.README_KEYPHRASES.value,
                              keyphrases)
                )

            tone = classify_readme_tone(self.text_content)
            if tone:
                stats.append(
                    Statistic(FileStatCollection.README_TONE.value, tone)
                )

            if not keyphrases or not tone:
                logger.info(
                    "README insights for %s: keyphrases=%d tone=%s",
                    self.relative_path,
                    len(keyphrases),
                    tone or "None",
                )

        self.stats.extend(stats)
