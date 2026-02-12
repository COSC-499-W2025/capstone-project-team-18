import sys
import types

from src.core.ML.models import model_runtime as mr


def _reset_zero_shot_runtime_state() -> None:
    mr._ZSC_PIPELINE_CACHE.clear()
    mr._ZSC_PIPELINE_FAILED.clear()


def test_remote_zero_shot_pipeline_used_when_server_ready(monkeypatch):
    _reset_zero_shot_runtime_state()
    monkeypatch.setenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_URL", "http://ml-server:8001")
    monkeypatch.delenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_REQUIRED", raising=False)

    calls: list[tuple[str, dict | None]] = []

    def fake_request(url: str, *, payload=None, timeout: float):
        calls.append((url, payload))
        if url.endswith("/health"):
            return {"ok": True}
        inputs = payload.get("inputs", []) if isinstance(payload, dict) else []
        return {
            "results": [
                {
                    "labels": ["feature implementation", "bug fix"],
                    "scores": [0.91, 0.09],
                }
                for _ in inputs
            ]
        }

    monkeypatch.setattr(mr, "_http_json_request", fake_request)

    classifier = mr.get_zero_shot_pipeline("facebook/bart-large-mnli")
    assert classifier is not None

    single = classifier(
        "feat: add auth endpoint",
        ["feature implementation", "bug fix"],
        multi_label=False,
    )
    assert single["labels"][0] == "feature implementation"

    batch = classifier(
        ["fix login bug", "test: add integration tests"],
        ["bug fix", "testing"],
        multi_label=False,
        batch_size=2,
    )
    assert isinstance(batch, list)
    assert len(batch) == 2
    assert batch[0]["labels"][0] == "feature implementation"

    cached_again = mr.get_zero_shot_pipeline("facebook/bart-large-mnli")
    assert cached_again is classifier
    assert any(url.endswith("/health") for url, _ in calls)
    assert any(url.endswith("/v1/zero-shot/classify") for url, _ in calls)


def test_zero_shot_falls_back_to_local_pipeline_when_server_unavailable(monkeypatch):
    _reset_zero_shot_runtime_state()
    monkeypatch.setenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_URL", "http://ml-server:8001")
    monkeypatch.delenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_REQUIRED", raising=False)
    monkeypatch.setattr(mr, "_http_json_request", lambda *_args, **_kwargs: None)

    sentinel_pipeline = object()
    fake_transformers = types.ModuleType("transformers")

    def fake_pipeline(task: str, *, model: str, local_files_only: bool):
        assert task == "zero-shot-classification"
        assert model == "facebook/bart-large-mnli"
        assert isinstance(local_files_only, bool)
        return sentinel_pipeline

    fake_transformers.pipeline = fake_pipeline
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    classifier = mr.get_zero_shot_pipeline("facebook/bart-large-mnli")
    assert classifier is sentinel_pipeline


def test_zero_shot_remote_required_disables_local_fallback(monkeypatch):
    _reset_zero_shot_runtime_state()
    monkeypatch.setenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_URL", "http://ml-server:8001")
    monkeypatch.setenv("ARTIFACT_MINER_ZERO_SHOT_SERVER_REQUIRED", "1")
    monkeypatch.setattr(mr, "_http_json_request", lambda *_args, **_kwargs: None)

    classifier = mr.get_zero_shot_pipeline("facebook/bart-large-mnli")
    assert classifier is None
