import re
from pathlib import Path

from src.core.statistic import Statistic, FileStatCollection, FileDomain
from src.core.analyzer.text_file_analyzer import TextFileAnalyzer
from src.core.ML.models.azure_model import AzureFoundryManager, EXTRACTION_PROMPT, ReadmeKeywordOutput
from src.infrastructure.log.logging import get_logger


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
        if filename.startswith("readme") and self.ml_consent:

            foundry = AzureFoundryManager()

            try:
                readme_extraction = foundry.process_request(
                    user_input=self.text_content,
                    system_prompt=EXTRACTION_PROMPT,
                    response_model=ReadmeKeywordOutput
                )

                # Pass the variables parsed from the data
                stats.append(Statistic(
                    FileStatCollection.README_TOOL_KEYPHRASES.value, readme_extraction.tool_keywords))
                stats.append(Statistic(
                    FileStatCollection.README_TASK_KEYPHRASES.value, readme_extraction.task_keywords))
                stats.append(
                    Statistic(FileStatCollection.README_TONE.value, readme_extraction.tone))

            except:
                # Either a internal server error or a failed validation. Either way move on without statistics
                pass

        self.stats.extend(stats)
