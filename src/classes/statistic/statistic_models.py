"""
This file contains custom classes and enumerations used for statistical analysis
in the project.
"""

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
    PYTHON = ("Python", [".py", ".pyw", ".pyx", ".pxd", ".pxi"])
    JAVASCRIPT = ("Javascript", [".js", ".jsx", ".mjs"])
    JAVA = ("Java", [".java", ".jar", ".class"])
    CPP = ("C++", [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h"])
    C = ("C", [".c", ".h"])
    CSHARP = ("C#", [".cs", ".csx"])
    PHP = ("PHP", [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"])
    RUBY = ("Ruby", [".rb", ".rbw", ".rake", ".gemspec"])
    SWIFT = ("Swift", [".swift"])
    GO = ("Go", [".go"])
    RUST = ("Rust", [".rs", ".rlib"])
    TYPESCRIPT = ("Typescript", [".ts", ".tsx"])
    HTML = ("HTML", [".html", ".htm", ".xhtml"])
    CSS = ("CSS", [".css", ".scss", ".sass", ".less"])
    SQL = ("SQL", [".sql", ".ddl", ".dml"])
    SHELL = ("Shell", [".sh", ".bash", ".zsh", ".fish"])
    R = ("R", [".R", ".r"])
