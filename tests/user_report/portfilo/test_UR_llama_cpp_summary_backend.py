from src.core.ML.models import llama_cpp_runtime as lcr
from src.core.ML.models.contribution_analysis import summary_generator as sg
from src.core.ML.models.contribution_analysis import project_summary_generator as psg


def _signature_facts():
    return sg.build_signature_facts(
        focus="Analytics",
        top_skills=["Python", "SQL", "FastAPI"],
        top_languages=["Python", "SQL"],
        tools=["FastAPI", "Pandas"],
        role="core_contributor",
        cadence="consistent",
        commit_focus="feature",
        themes=["analytics", "reporting"],
        activities=["consistent delivery cadence", "feature implementation"],
        emerging=["Generative AI"],
        project_names=["InternalProject"],
        tags=["dashboard"],
        experience_stage="early-career",
    )


def _project_facts():
    return psg.build_project_summary_facts(
        project_name="Insight Portal",
        goal_terms=["analytics", "reporting"],
        frameworks=["FastAPI"],
        languages=["Python"],
        role="core_contributor",
        commit_focus="feature",
        commit_pct=42.0,
        line_pct=40.0,
        activity_breakdown=[("code", 62.0)],
        role_description=None,
    )


def test_llama_cpp_json_generation_retries_once(monkeypatch):
    calls = {"count": 0}

    def fake_generate(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return '{"wrong":"shape"}'
        return '{"summary":"valid summary"}'

    monkeypatch.setattr(lcr, "_generate_raw_completion", fake_generate)

    parsed = lcr.llama_cpp_generate_json_object(
        model_path="/tmp/fake.gguf",
        prompt="test",
        validator=lambda payload: (
            isinstance(payload.get("summary"), str) and set(payload.keys()) == {"summary"},
            "invalid_payload",
        ),
        max_retries=1,
    )

    assert parsed == {"summary": "valid summary"}
    assert calls["count"] == 2


def test_signature_generator_prefers_llama_cpp_when_enabled(monkeypatch):
    summary = (
        "Early-career software contributor focused on analytics delivery and reliable backend services. "
        "Recent work uses Python, SQL, and FastAPI to ship feature updates with measurable outcomes. "
        "I communicate technical tradeoffs clearly and improve reporting workflows for both engineering and business stakeholders."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": summary})
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "Python" in output
    assert "FastAPI" in output


def test_signature_generator_llama_cpp_falls_back_when_invalid(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: None)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert len(output.split()) >= 30


def test_project_summary_generator_prefers_llama_cpp_when_enabled(monkeypatch):
    summary = (
        "The project focused on analytics and reporting outcomes for internal operations. "
        "It was implemented with FastAPI and Python for reliable service delivery. "
        "I contributed as a core contributor by authoring about 42% of commits focused on feature changes."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML", raising=False)
    monkeypatch.setattr(psg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(psg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(psg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": summary})
    psg._CACHE.clear()

    output = psg.generate_project_summary(_project_facts())

    assert output is not None
    assert "FastAPI" in output
    assert "42%" in output


def test_project_summary_generator_respects_require_ml_with_llama_failure(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML", "1")
    monkeypatch.setattr(psg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(psg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(psg, "llama_cpp_generate_json_object", lambda **_kwargs: None)
    psg._CACHE.clear()

    output = psg.generate_project_summary(_project_facts())

    assert output is None


def test_llama_cpp_auto_detects_local_gguf(monkeypatch, tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    gguf_path = models_dir / "phi-4-mini-q4_k_m.gguf"
    gguf_path.write_bytes(b"gguf")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARTIFACT_MINER_USE_LLAMA_CPP", raising=False)
    monkeypatch.delenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", raising=False)

    resolved = lcr.resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_SIGNATURE_MODEL_PATH")
    assert resolved == str(gguf_path.resolve())
    assert lcr.llama_cpp_enabled() is True


def test_signature_generator_repairs_short_llama_output(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": "Strong in Python."})
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_project_summary_generator_repairs_short_llama_output(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML", raising=False)
    monkeypatch.setattr(psg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(psg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(psg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": "FastAPI-based"})
    psg._CACHE.clear()

    facts = _project_facts()
    output = psg.generate_project_summary(facts)

    assert output is not None
    ok, reason = psg._is_valid_summary(output, facts)
    assert ok, reason
