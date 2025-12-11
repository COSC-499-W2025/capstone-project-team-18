"""
This file acts as a central hub for everything analyzer.
This makes it so we can just use

from src.classes.analyzer import PythonAnalyzer, HTMLAnalyzer

instead of

from src.classes.analyzer.python_analyzer import PythonAnalyzer
from src.classes.analyzer.html_analyzer import HTMLAnalyzer

This makes things a little cleaner.
"""

from .base_file_analyzer import BaseFileAnalyzer
from .c_analyzer import CAnalyzer
from .code_file_analyzer import CodeFileAnalyzer
from .css_analyzer import CSSAnalyzer
from .html_analyzer import HTMLAnalyzer
from .java_analyzer import JavaAnalyzer
from .java_script_analyzer import JavaScriptAnalyzer
from .natural_language_analyzer import NaturalLanguageAnalyzer
from .php_analyzer import PHPAnalyzer
from .python_analyzer import PythonAnalyzer
from .text_file_analyzer import TextFileAnalyzer
from .type_script_analyzer import TypeScriptAnalyzer
from .analyzer_util import extract_file_reports, get_appropriate_analyzer

__all__ = [
    "BaseFileAnalyzer",
    "CAnalyzer",
    "CodeFileAnalyzer",
    "CSSAnalyzer",
    "HTMLAnalyzer",
    "JavaAnalyzer",
    "JavaScriptAnalyzer",
    "NaturalLanguageAnalyzer",
    "PHPAnalyzer",
    "PythonAnalyzer",
    "TextFileAnalyzer",
    "TypeScriptAnalyzer",
    "extract_file_reports",
    "get_appropriate_analyzer"
]
