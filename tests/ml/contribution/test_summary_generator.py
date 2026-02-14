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
    monkeypatch.setattr(sg, "_load_model", lambda: (None, None))
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(_sample_facts())

    assert summary is not None
    assert "Python" in summary or "SQL" in summary or "Power BI" in summary
    assert 2 <= summary.count(".") <= 6
    assert 30 <= len(summary.split()) <= 140


def test_generate_signature_fallback_adapts_to_emerging_focus(monkeypatch):
    monkeypatch.setattr(sg, "_load_model", lambda: (None, None))
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(
        _sample_facts(
            focus="ML",
            emerging=["Generative AI", "Machine Learning"],
            top_skills=["Python", "PyTorch", "NLP"],
            tools=["Transformers", "PyTorch", "LangChain"],
        )
    )

    assert summary is not None
    assert "Generative AI" in summary or "Machine Learning" in summary


def test_generate_signature_fallback_uses_student_tone(monkeypatch):
    monkeypatch.setattr(sg, "_load_model", lambda: (None, None))
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(
        _sample_facts(
            experience_stage="student",
            focus="Analytics",
        )
    )

    assert summary is not None
    assert "student" in summary.lower() or "curious learner" in summary.lower()


def test_generate_signature_fallback_uses_experienced_tone(monkeypatch):
    monkeypatch.setattr(sg, "_load_model", lambda: (None, None))
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    sg._CACHE.clear()

    summary = sg.generate_signature(
        _sample_facts(
            experience_stage="experienced",
            role="leader",
            emerging=["Cloud Platforms"],
        )
    )

    assert summary is not None
    lowered = summary.lower()
    assert (
        "experienced software engineer" in lowered
        or "senior-level software engineer" in lowered
    )


def test_generate_signature_respects_require_ml_flag(monkeypatch):
    monkeypatch.setattr(sg, "_load_model", lambda: (None, None))
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
        "Web developer experienced in building web applications with HTML, CSS, and JavaScript. "
        "Experienced web developer building web applications with HTML, CSS, and JavaScript. "
        "Strong in Python and SQL for analytics and reporting across complex project delivery environments."
    )
    ok, reason = sg._is_valid_summary(redundant, _sample_facts())
    assert ok is False
    assert reason == "redundant_repetition"
