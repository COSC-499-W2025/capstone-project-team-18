import pytest

from src.core.ML.models.contribution_analysis import summary_generator as sg


def _sample_facts(**overrides):
    facts = sg.build_signature_facts(
        focus="Analytics",
        top_skills=["Python", "SQL", "Power BI"],
        top_languages=["Python", "SQL", "Java"],
        tools=["Pandas", "FastAPI", "Power BI"],
        role="core_contributor",
        cadence="consistent",
        commit_focus="feature",
        themes=["analytics", "reporting"],
        activities=["consistent delivery cadence", "feature implementation"],
        emerging=["Generative AI"],
        project_names=["InternalProject"],
        tags=["dashboard", "insights"],
        experience_stage="early-career",
    )
    facts.update(overrides)
    return facts


def test_generate_signature_uses_deterministic_fallback_when_model_unavailable(monkeypatch):
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(_sample_facts())

    assert summary is not None
    assert "Python" in summary or "SQL" in summary or "Power BI" in summary
    assert 2 <= summary.count(".") <= 6
    assert 30 <= len(summary.split()) <= 140


@pytest.mark.parametrize(
    "overrides, expected_phrases",
    [
        (
            {
                "focus": "ML",
                "emerging": ["Generative AI", "Machine Learning"],
                "top_skills": ["Python", "PyTorch", "NLP"],
                "tools": ["Transformers", "PyTorch", "LangChain"],
            },
            ("generative ai", "machine learning"),
        ),
        (
            {
                "experience_stage": "student",
                "focus": "Analytics",
            },
            ("student", "curious learner"),
        ),
        (
            {
                "experience_stage": "experienced",
                "role": "leader",
                "emerging": ["Cloud Platforms"],
            },
            ("experienced software engineer", "senior-level software engineer"),
        ),
    ],
)
def test_generate_signature_fallback_variants(monkeypatch, overrides, expected_phrases):
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(_sample_facts(**overrides))

    assert summary is not None
    summary_lower = summary.lower()
    assert any(phrase in summary_lower for phrase in expected_phrases)


def test_generate_signature_respects_require_ml_flag(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    sg._CACHE.clear()

    summary = sg.generate_signature(_sample_facts())

    assert summary is None


def test_polish_summary_removes_redundant_domain_sentences():
    raw = (
        "As a web developer, I have experience in developing and maintaining web applications using HTML, CSS, and JavaScript. "
        "I have also worked on data analysis and data visualization projects using Python and SQL. "
        "I am proficient in web development frameworks such as React and have experience with mobile development using Android Studio. "
        "I am also proficient in data analysis and data visualization using Python and SQL."
    )

    polished = sg._polish_summary(raw)

    assert polished
    assert polished.lower().count("data analysis and data visualization") == 0
    assert polished.lower().count("data analysis and visualization") <= 1
    assert polished.lower().count("web developer") <= 1


def test_validator_rejects_redundant_repetition():
    redundant = (
        "Web developer experienced in building web applications with HTML, CSS, and JavaScript for analytics teams. "
        "Experienced web developer building web applications with HTML, CSS, and JavaScript for analytics teams. "
        "Strong in Python and SQL for analytics and reporting in operational dashboard delivery."
    )
    ok, reason = sg._is_valid_summary(redundant, _sample_facts())
    assert ok is False
    assert reason == "redundant_repetition"


def test_generate_signature_does_not_cache_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(sg, "azure_openai_enabled", lambda: True)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_generate_signature_with_azure_openai", lambda _facts: None)
    calls = {"count": 0}

    def _fallback(_facts, *, context):
        calls["count"] += 1
        return f"Fallback summary {calls['count']}"

    monkeypatch.setattr(sg, "_validated_fallback_summary", _fallback)
    sg._CACHE.clear()

    summary_one = sg.generate_signature(_sample_facts())
    summary_two = sg.generate_signature(_sample_facts())

    assert summary_one == "Fallback summary 1"
    assert summary_two == "Fallback summary 2"
    assert calls["count"] == 2
