from src.core.analyzer.natural_language_analyzer import NaturalLanguageAnalyzer
from src.core.report import ProjectReport, FileReport
from src.core.statistic import (
    StatisticIndex,
    Statistic,
    FileStatCollection,
    ProjectStatCollection,
)
from src.core.ML.models.readme_analysis import keyphrase_extraction, readme_insights


def test_project_tags_from_readme_keyphrases():
    stats = StatisticIndex([
        Statistic(FileStatCollection.README_KEYPHRASES.value,
                  ["REST API", "OAuth", "PostgreSQL"]),
    ])
    file_report = FileReport(stats, filepath="README.md")

    report = ProjectReport(file_reports=[file_report],
                           project_name="ProjectTagsTest")

    tags = report.get_value(ProjectStatCollection.PROJECT_TAGS.value)
    assert tags == ["REST API", "OAuth", "PostgreSQL"]


def test_project_tags_from_readme_text(tmp_path, monkeypatch):
    readme_text = "API API API. This project exposes an API for clients."

    monkeypatch.setattr(
        keyphrase_extraction,
        "_extract_with_keybert",
        lambda text, top_n: ["API"] if "API" in text else [],
    )
    monkeypatch.setattr(
        readme_insights, "extract_readme_themes", lambda _text: [])
    monkeypatch.setattr(
        readme_insights, "classify_readme_tone", lambda _text: None)

    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "README.md").write_text(readme_text, encoding="utf-8")

    analyzer = NaturalLanguageAnalyzer(str(project_root), "README.md")
    file_report = analyzer.analyze()
    report = ProjectReport(file_reports=[file_report],
                           project_name="ProjectTagsTest")

    tags = report.get_value(ProjectStatCollection.PROJECT_TAGS.value)
    assert tags == ["API"]


def test_project_themes_from_readme_corpus(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    docs_root = project_root / "docs"
    docs_root.mkdir(parents=True)

    (project_root / "README.md").write_text(
        "API API API. This project exposes a public API.",
        encoding="utf-8",
    )
    (docs_root / "README.md").write_text(
        "Authentication and auth flows for API clients.",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        readme_insights,
        "extract_readme_themes_bulk",
        lambda _texts, max_themes=5: [["API"], ["Authentication"]],
    )

    file_reports = [
        FileReport(StatisticIndex(), filepath=str(project_root / "README.md")),
        FileReport(StatisticIndex(), filepath=str(docs_root / "README.md")),
    ]

    report = ProjectReport(
        file_reports=file_reports,
        project_name="ProjectThemesTest",
        project_path=str(project_root),
    )

    themes = report.get_value(ProjectStatCollection.PROJECT_THEMES.value)
    assert themes == ["API", "Authentication"]


def test_single_readme_themes_fallback(monkeypatch):
    monkeypatch.setattr(readme_insights, "_extract_topics",
                        lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        keyphrase_extraction,
        "extract_readme_keyphrases",
        lambda _text, top_n=5: ["API"][:top_n],
    )

    themes_by_doc = readme_insights.extract_readme_themes_bulk(["API API API"])
    assert themes_by_doc == [["API"]]
