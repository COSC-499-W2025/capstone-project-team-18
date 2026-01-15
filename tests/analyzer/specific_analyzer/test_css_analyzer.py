from src.core.analyzer import (
    CSSAnalyzer,
)


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

    analyzer = CSSAnalyzer(str(tmp_path), "example.css")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] == 4
    assert stats["NUMBER_OF_CLASSES"] == 4
    assert "theme.css" in stats["IMPORTED_PACKAGES"]


def test_css_analyzer_empty_file(tmp_path):
    css_file = tmp_path / "empty.css"
    css_file.write_text("")
    analyzer = CSSAnalyzer(str(tmp_path), "empty.css")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []
