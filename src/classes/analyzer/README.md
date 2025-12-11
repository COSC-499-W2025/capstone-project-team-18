# Overview

## Summary

The purpose of an analyzer class is to measure everything we can about a file. Although, there are different levels to this depending on a file type. We will get different information and we will retieve it differently if a file is a pdf or a python file. So, we define a family of many different analyzers and for every file, we try to give it to the most accurate analyzer.

The BaseFileAnalyzer is the basis for all these, we will always always know the size of a file in bytes, the created date, modified date, but that is all we know for a file.

Now, what if the file is text based? (.txt, .py, .md, etc) Then, we can create a TextFileAnalyzer that can make text based statistics (number of lines, words written, characters type, etc).

Now, what if that file is a python file? Well can get even more information about the file. Look for the import keyword in the file, are they importing a package often? Say, pandas? That probably means that they are skilled in that package and should make a statistic about that skill.

We keep building these analyzers out, image based analyzers, .R, .csv, .java, etc. At every specific analyzer class, we are creating as many statistics as possible with the given knowledge of it being a file, or text based, or python etc.

## Class Diagram

```mermaid
classDiagram

    %% =========================
    %% Base Classes
    %% =========================
    class BaseFileAnalyzer {
        <<abstract>>
        +path_to_top_level_project: str
        +relative_path: str
        +filepath: str
        +repo: Repo?
        +email: str?
        +language_filter: list[str]?
        +stats: StatisticIndex
        +blame_info
        +is_git_tracked: bool

        %% Statistics
        +DATE_CREATED
        +DATE_MODIFIED
        +FILE_SIZE_BYTES
    }

    class TextFileAnalyzer {
        +text_content: str

        %% Statistics
        +LINES_IN_FILE
        +PERCENTAGE_LINES_COMMITTED
    }

    class NaturalLanguageAnalyzer {
        %% Statistics
        +TYPE_OF_FILE = DOCUMENTATION
        +WORD_COUNT
        +CHARACTER_COUNT
        +SENTENCE_COUNT
    }

    class CodeFileAnalyzer {
        %% Statistics
        +TYPE_OF_FILE (CODE or TEST)
        +CODING_LANGUAGE
    }

    %% =========================
    %% Language-Specific Analyzers
    %% =========================

    class PythonAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES
        +IMPORTED_PACKAGES
    }

    class JavaAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES
        +IMPORTED_PACKAGES
    }

    class JavaScriptAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES
        +IMPORTED_PACKAGES
    }

    class CAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES   %% structs
        +IMPORTED_PACKAGES
    }

    class TypeScriptAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES
        +NUMBER_OF_INTERFACES
        +IMPORTED_PACKAGES
    }

    class CSSAnalyzer {
        +NUMBER_OF_FUNCTIONS   %% rule blocks
        +NUMBER_OF_CLASSES     %% CSS class selectors
        +IMPORTED_PACKAGES     %% @import
    }

    class HTMLAnalyzer {
        +NUMBER_OF_FUNCTIONS   %% script blocks
        +NUMBER_OF_CLASSES     %% class attributes
        +IMPORTED_PACKAGES     %% src/href resources
    }

    class PHPAnalyzer {
        +NUMBER_OF_FUNCTIONS
        +NUMBER_OF_CLASSES
        +NUMBER_OF_INTERFACES
        +IMPORTED_PACKAGES
    }

    %% =========================
    %% Inheritance
    %% =========================
    BaseFileAnalyzer <|-- TextFileAnalyzer
    TextFileAnalyzer <|-- NaturalLanguageAnalyzer
    TextFileAnalyzer <|-- CodeFileAnalyzer

    CodeFileAnalyzer <|-- PythonAnalyzer
    CodeFileAnalyzer <|-- JavaAnalyzer
    CodeFileAnalyzer <|-- JavaScriptAnalyzer
    CodeFileAnalyzer <|-- CAnalyzer
    CodeFileAnalyzer <|-- TypeScriptAnalyzer
    CodeFileAnalyzer <|-- CSSAnalyzer
    CodeFileAnalyzer <|-- HTMLAnalyzer
    CodeFileAnalyzer <|-- PHPAnalyzer
```
