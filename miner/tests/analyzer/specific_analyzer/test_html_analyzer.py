from src.core.analyzer import (
    HTMLAnalyzer,
)


def test_html_analyzer_classes_scripts_imports(tmp_path, get_ready_specific_analyzer):
    html_code = '''
<!doctype html>
<html>
  <head>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="app.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
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

    analyzer = get_ready_specific_analyzer(str(tmp_path), "index.html")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["NUMBER_OF_FUNCTIONS"] == 3  # 2 external + 1 inline
    assert stats["NUMBER_OF_CLASSES"] >= 4

    imports = set(stats["IMPORTED_PACKAGES"])
    # CDN libraries extracted by name
    assert "jquery" in imports
    assert "bootstrap" in imports
    # local files and images must not appear
    assert "app.js" not in imports
    assert "style.css" not in imports
    assert "logo.png" not in imports


def test_html_analyzer_local_only(tmp_path, get_ready_specific_analyzer):
    """Local scripts/stylesheets and images should never appear in IMPORTED_PACKAGES."""
    html_code = '''
<!doctype html>
<html>
  <head>
    <link rel="stylesheet" href="/static/main.css">
    <script src="./js/app.js"></script>
  </head>
  <body>
    <img src="images/banner.jpg" alt="">
  </body>
</html>
'''
    html_file = tmp_path / "local.html"
    html_file.write_text(html_code)

    analyzer = get_ready_specific_analyzer(str(tmp_path), "local.html")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()

    assert stats["IMPORTED_PACKAGES"] == []


def test_html_analyzer_empty_file(tmp_path, get_ready_specific_analyzer):
    html_file = tmp_path / "empty.htm"
    html_file.write_text("")
    analyzer = get_ready_specific_analyzer(str(tmp_path), "empty.htm")
    report = analyzer.analyze()
    stats = report.statistics.to_dict()
    assert stats["NUMBER_OF_FUNCTIONS"] == 0
    assert stats["NUMBER_OF_CLASSES"] == 0
    assert stats["IMPORTED_PACKAGES"] == []
