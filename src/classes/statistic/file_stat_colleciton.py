"""
This document logs all the different FILE statistics that can be collected.
"""

from enum import Enum
from datetime import date
from .base_classes import StatisticTemplate
from .statistic_models import FileDomain, CodingLanguage


class FileStatisticTemplate(StatisticTemplate):
    pass


class FileStatCollection(Enum):
    LINES_IN_FILE = FileStatisticTemplate(
        name="LINES_IN_FILE",
        description="number of lines in a file",
        expected_type=int,
    )

    DATE_CREATED = FileStatisticTemplate(
        name="DATE_CREATED",
        description="creation date of the file",
        expected_type=date,
    )

    DATE_MODIFIED = FileStatisticTemplate(
        name="DATE_MODIFIED",
        description="last date the file was modified",
        expected_type=date,
    )

    FILE_SIZE_BYTES = FileStatisticTemplate(
        name="FILE_SIZE_BYTES",
        description="number of bytes in the file",
        expected_type=int,
    )

    RATIO_OF_INDIVIDUAL_CONTRIBUTION = FileStatisticTemplate(
        name="RATIO_OF_INDIVIDUAL_CONTRIBUTION",
        description="amount of the file that was authored by the user",
        expected_type=float,
    )

    SKILLS_DEMONSTRATED = FileStatisticTemplate(
        name="SKILLS_DEMONSTRATED",
        description="the skills that where demonstrated in this file",
        expected_type=list[str],
    )

    TYPE_OF_FILE = FileStatisticTemplate(
        name="TYPE_OF_FILE",
        description="what is the purpose of this file?",
        expected_type=FileDomain,
    )

    WORD_COUNT = FileStatisticTemplate(
        name="WORD_COUNT",
        description="number of words in the file",
        expected_type=int,
    )

    CHARACTER_COUNT = FileStatisticTemplate(
        name="CHARACTER_COUNT",
        description="number of characters in the file",
        expected_type=int,
    )

    SENTENCE_COUNT = FileStatisticTemplate(
        name="SENTENCE_COUNT",
        description="number of sentences in the file",
        expected_type=int,
    )

    NUMBER_OF_FUNCTIONS = FileStatisticTemplate(
        name="NUMBER_OF_FUNCTIONS",
        description="number of functions in the file",
        expected_type=int,
    )

    NUMBER_OF_CLASSES = FileStatisticTemplate(
        name="NUMBER_OF_CLASSES",
        description="number of classes in the file",
        expected_type=int,
    )

    NUMBER_OF_INTERFACES = FileStatisticTemplate(
        name="NUMBER_OF_INTERFACES",
        description="number of interfaces in the file",
        expected_type=int,
    )

    IMPORTED_PACKAGES = FileStatisticTemplate(
        name="IMPORTED_PACKAGES",
        description="list of imported packages",
        expected_type=list,
    )

    # percentage is not greatest indicator as any minor change is associated with ownership
    PERCENTAGE_LINES_COMMITTED = FileStatisticTemplate(
        name="PERCENTAGE_LINES_COMMITTED",
        description="percentage of lines attributed to individal in file",
        expected_type=float,
    )

    CODING_LANGUAGE = FileStatisticTemplate(
        name="CODING_LANGUAGE",
        description="the coding language of the file",
        expected_type=CodingLanguage
    )
