from src.core.analyzer import (
    CSSAnalyzer,
    HTMLAnalyzer,
    PHPAnalyzer,
    get_appropriate_analyzer,
)
import pytest


def test_factory_routes_specific_analyzers(tmp_path):
    css = tmp_path / "a.css"
    css.write_text(".a{color:red}")
    html = tmp_path / "a.html"
    html.write_text("<!doctype html><html></html>")
    php = tmp_path / "a.php"
    php.write_text("<?php function f(){} ?>")

    assert isinstance(get_appropriate_analyzer(
        str(tmp_path), "a.css"), CSSAnalyzer)
    assert isinstance(get_appropriate_analyzer(
        str(tmp_path), "a.html"), HTMLAnalyzer)
    assert isinstance(get_appropriate_analyzer(
        str(tmp_path), "a.php"), PHPAnalyzer)


def test_create_with_analysis_nonexistent_file():
    """Test handling of nonexistent files."""
    # The analyzer will raise an exception, so we expect this to fail
    with pytest.raises(FileNotFoundError):
        get_appropriate_analyzer(
            "/nonexistent/path", "nonexistent.file")
