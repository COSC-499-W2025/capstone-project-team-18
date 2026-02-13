import json

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
        "Recent work uses Python, SQL, and FastAPI to ship feature updates with measurable outcomes across reporting workflows. "
        "I communicate technical tradeoffs clearly, improve data visibility for stakeholders, and maintain production-quality implementation standards."
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


def test_signature_generator_recovers_from_invalid_json_via_plain_text(monkeypatch):
    summary_text = (
        "Early-career software contributor focused on analytics delivery and reliable backend services. "
        "Recent work uses Python and FastAPI to deliver feature updates with measurable outcomes across analytics workflows. "
        "I communicate technical tradeoffs clearly for both engineering and business stakeholders while maintaining reliable implementation quality."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: None)
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: f"Summary: {summary_text}")
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "Python" in output
    assert "FastAPI" in output


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


def test_llama_cpp_enabled_with_server_url_without_local_gguf(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ARTIFACT_MINER_USE_LLAMA_CPP", raising=False)
    monkeypatch.delenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", raising=False)
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_SERVER_URL", "http://llm-server:8000")
    monkeypatch.delenv("ARTIFACT_MINER_LLAMA_CPP_SERVER_MODEL", raising=False)

    resolved = lcr.resolve_llama_cpp_model_path("ARTIFACT_MINER_LLAMA_CPP_SIGNATURE_MODEL_PATH")
    assert resolved == "local-llm"
    assert lcr.llama_cpp_enabled() is True


def test_llama_cpp_server_generation_uses_http_api(monkeypatch):
    class _FakeHTTPResponse:
        def __init__(self, payload: str):
            self._payload = payload

        def read(self) -> bytes:
            return self._payload.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    captured = {}

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeHTTPResponse('{"choices":[{"text":"{\\"summary\\": \\"ready\\"}"}]}')

    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_SERVER_URL", "http://llm-server:8000")
    monkeypatch.delenv("ARTIFACT_MINER_LLAMA_CPP_SERVER_MODEL", raising=False)
    monkeypatch.setattr(lcr, "_load_model", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("local GGUF load should not run in HTTP-server mode")
    ))
    monkeypatch.setattr(lcr.urllib.request, "urlopen", _fake_urlopen)

    payload = lcr.llama_cpp_generate_json_object(
        model_path="ignored-in-http-mode",
        prompt="test prompt",
        validator=lambda data: (
            isinstance(data.get("summary"), str),
            "missing_summary",
        ),
        max_retries=0,
    )

    assert payload == {"summary": "ready"}
    assert captured["url"] == "http://llm-server:8000/v1/completions"
    assert captured["body"]["model"] == "local-llm"
    assert captured["body"]["prompt"] == "test prompt"


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


def test_signature_generator_short_llama_output_is_logged_as_fallback(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": "Strong in Python."})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: None)

    info_logs: list[str] = []

    def _capture_info(message, *args, **_kwargs):
        rendered = message % args if args else str(message)
        info_logs.append(rendered)

    monkeypatch.setattr(sg.logger, "info", _capture_info)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert any("Signature summary generated from deterministic fallback" in line for line in info_logs)
    assert not any("Signature summary generated successfully via llama-cpp" in line for line in info_logs)


def test_professional_fallback_keeps_sentence_break_before_growth_clause():
    fallback = sg._build_professional_fallback(_signature_facts())

    assert fallback is not None
    assert "while currently expanding applied depth" in fallback.lower()
    assert "FastAPI Currently" not in fallback


def test_signature_normalization_strips_prompt_echo_artifacts():
    raw = (
        "With a steady cadence in backend development, the contributor specializes in Python and FastAPI. "
        "Their expertise extends to web services and machine learning applications. "
        "QUESTION: What stack technologies are you proficient with. "
        "ANSWER: I am skilled in React and Python."
    )

    normalized = sg._normalize_summary(raw)

    assert "QUESTION:" not in normalized
    assert "ANSWER:" not in normalized
    assert "What stack technologies" not in normalized


def test_signature_normalization_strips_final_summary_artifact():
    raw = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work delivered measurable outcomes using Python and FastAPI across analytics workflows. "
        "Final summary: With an."
    )

    normalized = sg._normalize_summary(raw)

    assert "Final summary:" not in normalized
    assert normalized.endswith("workflows.")


def test_signature_normalization_strips_inline_summary_artifact():
    raw = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work delivered measurable outcomes using Python and FastAPI across analytics workflows. "
        "Summary: I also communicate technical decisions clearly to stakeholders."
    )

    normalized = sg._normalize_summary(raw)

    assert "Summary:" not in normalized
    assert "I also communicate technical decisions clearly to stakeholders." in normalized


def test_signature_normalization_strips_inline_output_artifact():
    raw = (
        "Entry-to-mid-level software contributor focused on backend systems and service reliability. "
        "My expertise includes Python, FastAPI, and analytics delivery across service workflows. "
        "Output: Skilled Full-Stack Web Developer with proficiency in react and HTML5/CSS3."
    )

    normalized = sg._normalize_summary(raw)

    assert "Output:" not in normalized
    assert "Skilled Full-Stack Web Developer" not in normalized


def test_signature_generator_rejects_prompt_echo_artifacts(monkeypatch):
    bad_summary = (
        "With a steady cadence in backend development, the contributor specializes primarily in Python and FastAPI. "
        "Their expertise extends to web services with an emerging interest in machine learning applications. "
        "QUESTION: What stack technologies are you proficient with. "
        "You can say you're familiar with JavaScript and CSS."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": bad_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: None)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "QUESTION:" not in output
    assert "ANSWER:" not in output
    assert "you can say" not in output.lower()
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_strips_output_artifact_suffix(monkeypatch):
    bad_summary = (
        "Entry-to-mid-level software contributor focused on backend systems and service reliability. "
        "Recent work delivered measurable reliability gains using Python and FastAPI services. "
        "Output: Skilled Full-Stack Web Developer with proficiency in react and HTML5/CSS3."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": bad_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: None)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "Output:" not in output
    assert "Skilled Full-Stack Web Developer" not in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_strips_example_prompt_echo_artifacts(monkeypatch):
    bad_summary = (
        "Entry-to-mid-level contributor, their top skills include Data Analytics and Web Development with Python being their preferred language for coding projects. "
        "After reading the following context, you will see some pieces of example output below. Example 1: Input Draft As an experienced software engineer, I developed strong full-stack web development skills. "
        "Recent work delivered measurable reliability gains through Python and FastAPI service improvements across analytics workflows."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.delenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", raising=False)
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": bad_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: None)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    lowered = output.lower()
    assert "after reading" not in lowered
    assert "example 1" not in lowered
    assert "input draft" not in lowered
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_ml_polish_rewrites_instructional_tone(monkeypatch):
    draft_summary = (
        "With a steady cadence in backend development, the contributor specializes primarily in Python and fastapi. "
        "QUESTION: What stack technologies are you proficient with. "
        "You can say you're familiar with JavaScript and CSS."
    )
    polished_summary = (
        "Early-career software contributor with steady backend delivery using Python and FastAPI services. "
        "Recent work delivers web features with JavaScript and CSS while maintaining measurable reliability outcomes. "
        "I communicate technical decisions clearly to engineering and business stakeholders and continue expanding applied machine learning depth."
    )

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": draft_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", lambda **_kwargs: polished_summary)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "QUESTION:" not in output
    assert "you can say" not in output.lower()
    assert "FastAPI" in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_expands_short_ml_output_via_retry(monkeypatch):
    short_summary = (
        "Early-career software contributor focused on backend systems. "
        "Works with Python and FastAPI."
    )
    expanded_summary = (
        "Early-career software contributor focused on backend reliability using Python and FastAPI services. "
        "Recent work delivered feature and API improvements, automated validation checks, and improved service quality across analytics workflows. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders while expanding machine learning depth."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return "Short draft."
        if "TASK: USER_SUMMARY_EXPAND" in prompt and "Variant: specific" in prompt:
            return expanded_summary
        if "TASK: USER_SUMMARY_EXPAND" in prompt:
            return expanded_summary
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": short_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "automated validation checks" in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_ranks_multiple_polish_candidates(monkeypatch):
    raw_summary = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable improvements across service workflows and API reliability for analytics operations. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders while expanding machine learning depth."
    )
    primary_polish = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "My expertise extends to Python and FastAPI across web workflows with measurable outcomes in delivery. "
        "I communicate technical work clearly for engineering and business stakeholders while expanding machine learning depth."
    )
    alternative_polish = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered API and workflow improvements, automated validation checks, and measurable reliability gains across analytics services. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders while expanding applied machine learning depth."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "Rewrite style variant: primary" in prompt:
            return alternative_polish
        if "Rewrite style variant: alternative" in prompt:
            return primary_polish
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": raw_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "automated validation checks" in output
    assert "expertise extends to" not in output.lower()
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_applies_fluency_polish_when_better(monkeypatch):
    raw_summary = (
        "Leveraging Python and FastAPI, I consistently contribute to backend projects for web delivery. "
        "My expertise in Web Development has enabled reliable solutions that delivered automated process improvements and measurable outcomes. "
        "With a strong foundation in Data Analytics using React and JavaScript, I communicate technical decisions to engineering and business stakeholders."
    )
    fluent_summary = (
        "Early-career software contributor focused on backend project delivery using Python and FastAPI. "
        "Recent work delivered reliable web service improvements, automated processes, and measurable outcomes for operational stakeholders. "
        "I also apply Data Analytics and React experience to communicate technical decisions clearly for engineering and business audiences."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return None
        if "TASK: USER_SUMMARY_FLUENCY_REWRITE" in prompt:
            return fluent_summary
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": raw_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "I also apply Data Analytics and React experience" in output
    assert "With a strong foundation" not in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_applies_resume_style_mold_when_better(monkeypatch):
    raw_summary = (
        "With a strong foundation in Web Development using JavaScript, CSS, and React, my steady contributions improved delivery outcomes. "
        "Leveraging Python and FastAPI expertise has significantly supported backend service development and reliability. "
        "Summary: My journey as an early-career contributor focuses on backend reliability."
    )
    molded_summary = (
        "Early-career software contributor focused on backend delivery and service reliability using Python and FastAPI. "
        "Recent work delivered measurable improvements through reliable implementation across web development workflows with JavaScript, CSS, and React. "
        "I also communicate technical decisions clearly for engineering and business stakeholders while continuing to deepen backend expertise."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return None
        if "TASK: USER_SUMMARY_RESUME_MOLD" in prompt and "Variant: primary" in prompt:
            return molded_summary
        if "TASK: USER_SUMMARY_RESUME_MOLD" in prompt:
            return molded_summary
        if "TASK: USER_SUMMARY_FLUENCY_REWRITE" in prompt:
            return None
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": raw_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "Summary:" not in output
    assert "My journey" not in output
    assert "I also communicate technical decisions clearly" in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_keeps_original_when_resume_style_mold_is_weaker(monkeypatch):
    raw_summary = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable reliability gains and automated workflow checks across web services. "
        "I also communicate technical tradeoffs clearly for engineering and business stakeholders while expanding applied Data Analytics depth."
    )
    weaker_mold = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable reliability gains and automated workflow checks across web services. "
        "My journey as an early-career contributor focuses on backend reliability."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return None
        if "TASK: USER_SUMMARY_RESUME_MOLD" in prompt:
            return weaker_mold
        if "TASK: USER_SUMMARY_FLUENCY_REWRITE" in prompt:
            return None
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": raw_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "My journey" not in output
    assert "I also communicate technical tradeoffs clearly" in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_generator_keeps_original_when_fluency_polish_is_weaker(monkeypatch):
    raw_summary = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable reliability gains and automated workflow checks across web services. "
        "I also communicate technical tradeoffs clearly for engineering and business stakeholders while expanding applied Data Analytics depth."
    )
    weaker_fluency = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable reliability gains and automated workflow checks across web services. "
        "With a strong foundation in Data Analytics, I communicate technical tradeoffs clearly for engineering and business stakeholders."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return None
        if "TASK: USER_SUMMARY_FLUENCY_REWRITE" in prompt:
            return weaker_fluency
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": raw_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "With a strong foundation" not in output
    assert "I also communicate technical tradeoffs clearly" in output
    ok, reason = sg._is_valid_summary(output, _signature_facts())
    assert ok, reason


def test_signature_validator_rejects_question_like_tone(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Early-career software contributor focused on backend reliability and service quality using Python and FastAPI. "
        "What stack technologies are used most often in this profile."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "question_like_tone"


def test_signature_generator_require_ml_rejects_short_llama_output(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": "Strong in Python."})
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is None


def test_resolve_experience_stage_with_ml_accepts_non_json_when_confident(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_STAGE_CLASSIFIER_ENABLE", "1")
    monkeypatch.setenv("ARTIFACT_MINER_STAGE_CLASSIFIER_MIN_CONF", "0.75")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: None)
    monkeypatch.setattr(
        sg,
        "llama_cpp_generate_text",
        lambda **_kwargs: "stage=early-career; confidence=0.86; rationale=project span and delivery volume",
    )

    stage = sg.resolve_experience_stage_with_ml(
        baseline_stage="student",
        project_count=5,
        active_months=18.0,
        role="core_contributor",
        top_skills=["Python", "FastAPI"],
        top_languages=["Python"],
        tools=["FastAPI"],
        professional_project_count=3,
        experimental_project_count=1,
        educational_project_count=1,
    )

    assert stage == "early-career"


def test_resolve_experience_stage_with_ml_rejects_non_adjacent_override(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_STAGE_CLASSIFIER_ENABLE", "1")
    monkeypatch.setenv("ARTIFACT_MINER_STAGE_CLASSIFIER_MIN_CONF", "0.75")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: None)
    monkeypatch.setattr(
        sg,
        "llama_cpp_generate_text",
        lambda **_kwargs: "stage=experienced; confidence=0.95; rationale=strong delivery",
    )

    stage = sg.resolve_experience_stage_with_ml(
        baseline_stage="student",
        project_count=2,
        active_months=6.0,
        role="contributor",
        top_skills=["Python"],
        top_languages=["Python"],
        tools=["FastAPI"],
        professional_project_count=0,
        experimental_project_count=2,
        educational_project_count=0,
    )

    assert stage == "student"


def test_signature_facts_include_proficiency_level():
    facts = _signature_facts()

    assert facts["experience_stage"] == "early-career"
    assert facts["proficiency_level"] == "Entry-to-mid-level"


def test_signature_repair_injects_proficiency_in_opening(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    facts = _signature_facts()
    summary = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work delivered measurable reliability gains through Python and FastAPI service improvements, observability automation, and structured release validation. "
        "I also communicate technical tradeoffs clearly for engineering and business stakeholders while documenting decisions and implementation outcomes."
    )

    repaired = sg._repair_summary_with_grounded_fallback(summary, facts, allow_fallback=False)

    assert repaired is not None
    first_sentence = sg._split_sentences(repaired)[0]
    assert "entry-to-mid-level" in first_sentence.lower()


def test_signature_repair_rewrites_top_skills_opening_to_professional_stage(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    facts = _signature_facts()
    summary = (
        "Their top skills include Data Analytics and Web Development with Python being their preferred language for coding projects. "
        "Recent work delivered measurable reliability gains through Python and FastAPI service improvements, observability automation, and structured release validation. "
        "I also communicate technical tradeoffs clearly for engineering and business stakeholders while documenting decisions and implementation outcomes."
    )

    repaired = sg._repair_summary_with_grounded_fallback(summary, facts, allow_fallback=False)

    assert repaired is not None
    first_sentence = sg._split_sentences(repaired)[0].lower()
    assert "entry-to-mid-level" in first_sentence
    assert "top skills include" not in first_sentence


def test_signature_validator_accepts_fuzzy_anchor_token_overlap(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    facts = sg.build_signature_facts(
        focus="DevOps",
        top_skills=["CI/CD"],
        top_languages=[],
        tools=[],
        role="core_contributor",
        cadence="consistent",
        commit_focus="feature",
        themes=[],
        activities=["delivery"],
        emerging=[],
        project_names=[],
        tags=[],
        experience_stage="early-career",
    )
    summary = (
        "Early-career software contributor focused on backend reliability and release quality. "
        "Recent work improved CI pipelines, automated checks, and delivery reliability for release workflows. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders while maintaining measurable implementation standards."
    )

    ok, reason = sg._is_valid_summary(summary, facts)

    assert ok, reason


def test_signature_validator_rejects_when_anchor_missing(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    facts = sg.build_signature_facts(
        focus="Backend",
        top_skills=["FastAPI"],
        top_languages=[],
        tools=[],
        role="core_contributor",
        cadence="consistent",
        commit_focus="feature",
        themes=[],
        activities=["delivery"],
        emerging=[],
        project_names=[],
        tags=[],
        experience_stage="early-career",
    )
    summary = (
        "Early-career software contributor focused on backend reliability and service quality. "
        "Recent work improved release cadence, automated checks, and delivery reliability across backend workflows. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders while maintaining measurable implementation standards."
    )

    ok, reason = sg._is_valid_summary(summary, facts)

    assert not ok
    assert reason == "no_skill_language_tool_anchor"


def test_signature_validator_rejects_generic_resume_tone(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "With a steady cadence in backend development, I am proficient primarily in Python and FastAPI systems. "
        "My expertise extends to web workflows and emerging interest in machine learning applications with measurable outcomes. "
        "I communicate technical tradeoffs clearly for engineering and business stakeholders during delivery."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "generic_resume_tone"


def test_signature_validator_rejects_rewritten_prefix_artifact(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Rewritten with entry-level proficiency focused primarily on DevOps practices using Python and React. "
        "Recent work delivered measurable outcomes through reliable implementation across release workflows and platform operations. "
        "I communicate technical tradeoffs clearly to engineering and business stakeholders."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "prompt_echo"


def test_signature_validator_rejects_labelled_noise_artifact(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Version 2: Entry-to-mid-level software contributor focused on DevOps and platform operations with Python and React. "
        "Recent work delivered measurable outcomes through reliable implementation across release workflows. "
        "I communicate technical tradeoffs clearly to engineering and business stakeholders."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason in {"prompt_echo", "noise_artifact"}


def test_signature_validator_rejects_instructional_noise_artifact(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Entry-to-mid-level software contributor focused on DevOps and platform operations with Python and React. "
        "Please ensure the summary highlights measurable outcomes through reliable implementation across release workflows. "
        "I communicate technical tradeoffs clearly to engineering and business stakeholders."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "noise_artifact"


def test_signature_validator_rejects_second_person_profile_voice(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "As an Entry-level student contributor with a steady cadence, I focus on DevOps and am actively learning Python for Web Development. "
        "My emerging interest lies in Data Engineering delivering measurable outcomes through reliable implementation. "
        "Your entry-level experience as a dedicated Student Contributor has centered around the dynamic field of DevOps while steadily honing your skills through consistent engagement over time."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "noise_artifact"


def test_signature_validator_rejects_mixed_person_voice(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Entry-to-mid-level software contributor focused on DevOps and platform reliability. "
        "I deliver measurable outcomes through reliable implementation across release workflows and service operations. "
        "Your profile demonstrates consistent growth across engineering initiatives and stakeholder communication."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "second_person_tone"


def test_signature_validator_rejects_meta_narration(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Entry-to-mid-level software contributor focused on DevOps and platform operations with Python and React. "
        "Recent work delivered measurable outcomes through reliable implementation and steady execution across release workflows. "
        "This summary highlights profile strengths in communication and growth across engineering initiatives."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "noise_artifact"


def test_signature_validator_rejects_meta_summary_marker(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work delivered measurable outcomes through Python and FastAPI service improvements for analytics workflows. "
        "Final summary: I communicate technical tradeoffs clearly to stakeholders."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "meta_summary_marker"


def test_signature_validator_rejects_fragment_sentence(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Early-career software contributor focused on backend systems and service reliability using Python and FastAPI. "
        "Recent work delivered measurable outcomes and reliability gains across analytics workflows for engineering stakeholders. "
        "With an."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert not ok
    assert reason == "fragment_sentence"


def test_signature_validator_accepts_professional_delivery_language(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    summary = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work reflects measurable engineering outcomes through clear, outcome-oriented implementation across analytics workflows. "
        "Core strengths include Python and FastAPI, with consistent communication of technical tradeoffs to engineering and business stakeholders."
    )

    ok, reason = sg._is_valid_summary(summary, _signature_facts())

    assert ok, reason


def test_signature_repair_injects_delivery_signal_when_missing(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    facts = _signature_facts()
    summary = (
        "Entry-to-mid-level software contributor focused on backend systems and platform architecture with Python and FastAPI. "
        "Recent work centers on analytics workflows, stakeholder communication, and platform coordination across engineering initiatives. "
        "Core strengths include Python, FastAPI, and React while expanding applied machine learning depth through portfolio work."
    )
    initial_ok, initial_reason = sg._is_valid_summary(summary, facts)
    assert not initial_ok
    assert initial_reason == "missing_delivery_signal"

    repaired = sg._repair_summary_with_grounded_fallback(summary, facts, allow_fallback=False)

    assert repaired is not None
    assert sg._has_delivery_or_outcome_signal(repaired)
    ok, reason = sg._is_valid_summary(repaired, facts)
    assert ok, reason


def test_signature_generator_retries_expansion_for_missing_delivery_signal(monkeypatch):
    initial_summary = (
        "Early-career software contributor focused on backend systems and service reliability. "
        "Recent work centers on analytics workflows and stakeholder communication across platform initiatives. "
        "Core strengths include Python and FastAPI with growing machine learning exposure."
    )
    expanded_summary = (
        "Early-career software contributor focused on backend systems and service reliability with Python and FastAPI. "
        "Recent work delivered measurable reliability gains through analytics workflow improvements, clearer technical handoffs, and stronger implementation quality. "
        "I communicate technical tradeoffs effectively for engineering and business stakeholders while expanding applied machine learning depth."
    )

    def _fake_text(**kwargs):
        prompt = kwargs.get("prompt", "")
        if "TASK: USER_SUMMARY_REWRITE" in prompt:
            return None
        if "TASK: USER_SUMMARY_EXPAND" in prompt:
            return expanded_summary
        return None

    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": initial_summary})
    monkeypatch.setattr(sg, "llama_cpp_generate_text", _fake_text)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is not None
    assert "delivered measurable reliability gains" in output.lower()
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


def test_project_summary_generator_require_ml_rejects_short_llama_output(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_PROJECT_SUMMARY_REQUIRE_ML", "1")
    monkeypatch.setattr(psg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(psg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))
    monkeypatch.setattr(psg, "llama_cpp_generate_json_object", lambda **_kwargs: {"summary": "FastAPI-based"})
    psg._CACHE.clear()

    output = psg.generate_project_summary(_project_facts())

    assert output is None


def test_signature_generator_logs_llama_rejection_reason(monkeypatch):
    monkeypatch.setenv("ARTIFACT_MINER_USE_LLAMA_CPP", "1")
    monkeypatch.setenv("ARTIFACT_MINER_LLAMA_CPP_MODEL_PATH", "/tmp/fake.gguf")
    monkeypatch.setenv("ARTIFACT_MINER_SIGNATURE_REQUIRE_ML", "1")
    monkeypatch.setattr(sg, "ml_extraction_allowed", lambda: True)
    monkeypatch.setattr(sg, "_load_model", lambda: (_ for _ in ()).throw(AssertionError("HF path should not run")))

    invalid_summary = (
        "This profile summarizes broad software delivery across multiple product contexts and release cycles. "
        "The narrative emphasizes communication and planning discipline with measurable outcomes for stakeholders. "
        "It intentionally avoids naming concrete tools, languages, or frameworks while remaining generic."
    )

    def _fake_llama_cpp_generate_json_object(**kwargs):
        validator = kwargs["validator"]
        validator({"summary": invalid_summary})
        return None

    warnings: list[str] = []

    def _capture_warning(message, *args, **_kwargs):
        rendered = message % args if args else str(message)
        warnings.append(rendered)

    monkeypatch.setattr(sg, "llama_cpp_generate_json_object", _fake_llama_cpp_generate_json_object)
    monkeypatch.setattr(sg.logger, "warning", _capture_warning)
    sg._CACHE.clear()

    output = sg.generate_signature(_signature_facts())

    assert output is None
    assert any(
        reason in line
        for line in warnings
        for reason in (
            "no_skill_language_tool_anchor",
            "generic_resume_tone",
            "missing_delivery_signal",
            "sentence_count=",
            "word_count=",
        )
    )
    assert any("llama-cpp signature generation failed validation/response" in line for line in warnings)
