"""
This file contains custom classes and enumerations used for statistical analysis
in the project.
"""

from typing import Dict, List
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict

# These are data classes. The purpose of these is sometimes a statistic needs
# to hold many types of data instead of just one value. For example, WeightedSkills
# doesn't just have the skill_name, but also a weight attached to it.


@dataclass
class WeightedSkills:
    skill_name: str
    weight: float

    def __lt__(self, other: "WeightedSkills"):
        return self.weight < other.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "weight": self.weight
        }


class FileDomain(Enum):
    DESIGN = "design"
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"


class CodingLanguage(Enum):
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    JAVA = "Java"
    CPP = "C++"
    C = "C"
    CSHARP = "C#"
    PHP = "PHP"
    RUBY = "Ruby"
    SWIFT = "Swift"
    GO = "Go"
    RUST = "Rust"
    TYPESCRIPT = "TypeScript"
    HTML = "HTML"
    CSS = "CSS"
    SQL = "SQL"
    SHELL = "Shell"
    R = "R"


LANGUAGE_EXTENSIONS: Dict[CodingLanguage, List[str]] = {
    CodingLanguage.PYTHON: [".py", ".pyw", ".pyx", ".pxd", ".pxi"],
    CodingLanguage.JAVASCRIPT: [".js", ".jsx", ".mjs"],
    CodingLanguage.JAVA: [".java", ".jar", ".class"],
    CodingLanguage.CPP: [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h"],
    CodingLanguage.C: [".c", ".h"],
    CodingLanguage.CSHARP: [".cs", ".csx"],
    CodingLanguage.PHP: [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"],
    CodingLanguage.RUBY: [".rb", ".rbw", ".rake", ".gemspec"],
    CodingLanguage.SWIFT: [".swift"],
    CodingLanguage.GO: [".go"],
    CodingLanguage.RUST: [".rs", ".rlib"],
    CodingLanguage.TYPESCRIPT: [".ts", ".tsx"],
    CodingLanguage.HTML: [".html", ".htm", ".xhtml"],
    CodingLanguage.CSS: [".css", ".scss", ".sass", ".less"],
    CodingLanguage.SQL: [".sql", ".ddl", ".dml"],
    CodingLanguage.SHELL: [".sh", ".bash", ".zsh", ".fish"],
    CodingLanguage.R: [".R", ".r"],
}
