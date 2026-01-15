from src.core.analyzer import (
    HTMLAnalyzer,
)


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

    analyzer = HTMLAnalyzer(str(tmp_path), "index.html")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] == 2
    assert stats["NUMBER_OF_CLASSES"] >= 4
    imports = set(stats["IMPORTED_PACKAGES"])
    assert {"app.js", "style.css", "logo.png"} <= imports


def test_html_analyzer_empty_file(tmp_path):
    html_file = tmp_path / "empty.htm"
    html_file.write_text("")
    analyzer = HTMLAnalyzer(str(tmp_path), "empty.htm")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []
