import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
CLASSES_DIR = SRC_DIR / "classes"

for p in (str(CLASSES_DIR), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.classes.analyzer import (  
    CSSAnalyzer,
    HTMLAnalyzer,
    PHPAnalyzer,
    get_appropriate_analyzer,
)

# ---------- CSS ----------
def test_css_analyzer_rules_classes_imports(tmp_path):
    css_code = '''
@import url("theme.css");
.btn { color: red; }
#title { font-weight: bold; }
.card.primary { padding: 1rem; }
@media (min-width: 600px) { .responsive { display: block; } }
'''
    css_file = tmp_path / "example.css"
    css_file.write_text(css_code)

    analyzer = CSSAnalyzer(str(css_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] >= 4
    assert stats["NUMBER_OF_CLASSES"] >= 4
    assert "theme.css" in stats["IMPORTED_PACKAGES"]

def test_css_analyzer_empty_file(tmp_path):
    css_file = tmp_path / "empty.css"
    css_file.write_text("")
    analyzer = CSSAnalyzer(str(css_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []

# ---------- HTML ----------
def test_html_analyzer_classes_scripts_imports(tmp_path):
    html_code = '''
<!doctype html>
<html>
  <head>
    <link rel="stylesheet" href="style.css">
    <script src="app.js"></script>
  </head>
  <body class="container main">
    <div class="container"><button class="btn primary">Click</button></div>
    <img src="logo.png" alt="logo">
    <script>console.log("inline")</script>
  </body>
</html>
'''
    html_file = tmp_path / "index.html"
    html_file.write_text(html_code)

    analyzer = HTMLAnalyzer(str(html_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] == 2     
    assert stats["NUMBER_OF_CLASSES"] >= 4       
    imports = set(stats["IMPORTED_PACKAGES"])
    assert {"app.js", "style.css", "logo.png"} <= imports

def test_html_analyzer_empty_file(tmp_path):
    html_file = tmp_path / "empty.htm"
    html_file.write_text("")
    analyzer = HTMLAnalyzer(str(html_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []

# ---------- PHP ----------
def test_php_analyzer_classes_interfaces_functions_imports(tmp_path):
    php_code = r'''<?php
use Some\Lib;
use Vendor\Package\Sub\Thing;

include_once("util.php");
require('config.php');

class MyClass {
    public function methodA() {}
}
interface IMyInterface {}

function foo() { return 42; }
$anon = fn($x) => $x + 1;
'''
    php_file = tmp_path / "example.php"
    php_file.write_text(php_code)

    analyzer = PHPAnalyzer(str(php_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] >= 2  # named + short arrow
    assert stats["NUMBER_OF_CLASSES"] == 1
    assert stats["NUMBER_OF_INTERFACES"] == 1

    imports = set(stats["IMPORTED_PACKAGES"])
    assert "util.php" in imports and "config.php" in imports
    normalized = {s.replace("\\", "/") for s in imports}
    assert "Some/Lib" in normalized
    assert any(s.endswith("Thing") for s in imports)

def test_php_analyzer_empty_file(tmp_path):
    php_file = tmp_path / "empty.php"
    php_file.write_text("<?php ?>")
    analyzer = PHPAnalyzer(str(php_file))
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["NUMBER_OF_INTERFACES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []

# ---------- Factory smoke test ----------
def test_factory_routes_specific_analyzers(tmp_path):
    css = tmp_path / "a.css";  css.write_text(".a{color:red}")
    html = tmp_path / "a.html"; html.write_text("<!doctype html><html></html>")
    php = tmp_path / "a.php";  php.write_text("<?php function f(){} ?>")

    assert isinstance(get_appropriate_analyzer(str(css)), CSSAnalyzer)
    assert isinstance(get_appropriate_analyzer(str(html)), HTMLAnalyzer)
    assert isinstance(get_appropriate_analyzer(str(php)), PHPAnalyzer)