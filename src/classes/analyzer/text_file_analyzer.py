import logging
from charset_normalizer import from_path
from git import InvalidGitRepositoryError
import logging

from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.base_file_analyzer import BaseFileAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextFileAnalyzer(BaseFileAnalyzer):
    """
    Analyzer for text-based files. Extends `BaseFileAnalyzer`.

    This class will parse a file that contains text and log the
    raw line count, but more specific type of stats are given
    to the subclasses which are: `CodeFileAnalyzer` and
    `NaturalLanguageAnalyzer`.

    Attributes:
        text_context (str): The string representation of the text in the file

    Statistics:
        - `LINES_IN_FILE`
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

        self._get_file_commit_percentage()
        self.stats.extend(stats)

    def _get_file_commit_percentage(self) -> None:
        """
        Calculate the percentage of lines in the file
        that were authored by the user with the given email.
        """

        # If the file is not tracked by git or email is None, return None
        if self.is_git_tracked is False or self.email is None or self.repo is None:
            return

        file_percent = None

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
                file_percent = 0.0
            else:
                file_percent = round((commit_count / line_count) * 100, 2)
        except InvalidGitRepositoryError as e:
            logger.debug(f"InvalidGitRepositoryError: {e}")
            return
        except Exception as e:
            logger.debug(f"Exception while computing commit percentage: {e}")
            return

        if file_percent is not None:
            self.stats.add(Statistic(FileStatCollection.PERCENTAGE_LINES_COMMITTED.value,
                                     file_percent))
