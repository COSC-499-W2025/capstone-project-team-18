"""
This file defines the SpecificCodeAnalyzer class.
"""

from abc import ABC, abstractmethod
from src.classes.statistic import Statistic, FileStatCollection
from src.classes.analyzer.code_file_analyzer import CodeFileAnalyzer


class SpecificCodeAnalyzer(CodeFileAnalyzer, ABC):
    """
    This class provides a empty file check before
    the file is sent down to the coding language specifc
    analyzers. This ensures that we don't send, for example,
    a empty java file to the Java Analyzer and rather just set
    everything to zero and move on.
    """

    def _process(self) -> None:
        super()._process()

        if not self.text_content.strip():
            # File is empty.
            self.stats.extend([
                Statistic(FileStatCollection.NUMBER_OF_FUNCTIONS.value, 0),
                Statistic(FileStatCollection.NUMBER_OF_CLASSES.value, 0),
                Statistic(FileStatCollection.IMPORTED_PACKAGES.value, []),
                Statistic(FileStatCollection.NUMBER_OF_INTERFACES.value, 0),
            ])

            return

        self._process_not_empty()

    @abstractmethod
    def _process_not_empty(self):
        """
        Sub classes overight this class to do normal _process method.
        """
        raise NotImplementedError(
            "A subclass did not overide the _process_not_empty function and it is being called in SpecificCodeAnalyzer")
