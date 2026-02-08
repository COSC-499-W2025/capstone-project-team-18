from src.core.analyzer import (
    PHPAnalyzer,
)


def test_php_analyzer_classes_interfaces_functions_imports(tmp_path, get_ready_specific_analyzer):
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

    analyzer = get_ready_specific_analyzer(str(tmp_path), "example.php")
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


def test_php_analyzer_empty_file(tmp_path, get_ready_specific_analyzer):
    php_file = tmp_path / "empty.php"
    php_file.write_text("<?php ?>")
    analyzer = get_ready_specific_analyzer(str(tmp_path), "empty.php")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["NUMBER_OF_INTERFACES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []
