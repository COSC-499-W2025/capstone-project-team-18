"""
Tests for portfolio API endpoints.

Covers all portfolio routes including the new three-part structure:
  Part A — narrative sections (block edit, conflicts, resolve)
  Part B — showcase flag (toggle via /cards/{name}/showcase)
  Part C — project card gallery (list, filter, edit overrides)
  Export  — static web portfolio ZIP download
"""
import io
import json
import zipfile
from datetime import datetime, date
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from src.database.api.models import (
    PortfolioModel,
    PortfolioSectionModel,
    BlockModel,
    PortfolioProjectCardModel,
    ProjectReportModel,
)


# ---------------------------------------------------------------------------
# Helpers — direct DB insertion (no service layer)
# ---------------------------------------------------------------------------

def _make_portfolio(engine, *, title="Test Portfolio", mode="private", project_ids=None) -> int:
    """Insert a minimal PortfolioModel, return its id."""
    with Session(engine) as session:
        p = PortfolioModel(
            title=title,
            mode=mode,
            creation_time=datetime.now(),
            last_updated_at=datetime.now(),
            project_ids_include=project_ids or [],
        )
        session.add(p)
        session.commit()
        session.refresh(p)
        return p.id


def _make_section(engine, portfolio_id: int, *, section_id="summary", title="Summary") -> int:
    """Insert a PortfolioSectionModel, return its id."""
    with Session(engine) as session:
        s = PortfolioSectionModel(
            portfolio_id=portfolio_id,
            section_id=section_id,
            title=title,
            order=0,
            block_order=["main_block"],
        )
        session.add(s)
        session.commit()
        session.refresh(s)
        return s.id


def _make_block(engine, section_db_id: int, *, tag="main_block", content="Hello world",
                in_conflict=False, conflict_content=None) -> int:
    """Insert a BlockModel with TextBlock content, return its id."""
    with Session(engine) as session:
        b = BlockModel(
            section_id=section_db_id,
            tag=tag,
            content_type="Text",
            current_content=content,
            in_conflict=in_conflict,
            conflict_content=conflict_content,
        )
        session.add(b)
        session.commit()
        session.refresh(b)
        return b.id


def _make_card(engine, portfolio_id: int, project_name: str, *,
               themes=None, tones="professional", tags=None, skills=None,
               frameworks=None, is_showcase=False, summary="A test project.") -> int:
    """Insert a PortfolioProjectCardModel, return its id."""
    with Session(engine) as session:
        c = PortfolioProjectCardModel(
            portfolio_id=portfolio_id,
            project_name=project_name,
            summary=summary,
            themes=themes or ["web"],
            tones=tones,
            tags=tags or ["python", "api"],
            skills=skills or ["Python", "FastAPI"],
            frameworks=frameworks or ["FastAPI"],
            languages={"Python": 0.8, "JavaScript": 0.2},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
            is_group_project=False,
            collaboration_role="Lead",
            work_pattern="consistent",
            commit_type_distribution={"feature": 60.0, "bugfix": 40.0},
            activity_metrics={"avg_commits_per_week": 3.5},
            is_showcase=is_showcase,
        )
        session.add(c)
        session.commit()
        session.refresh(c)
        return c.id


def _make_project_report(engine, name: str):
    """Insert a minimal ProjectReportModel."""
    with Session(engine) as session:
        session.add(ProjectReportModel(
            project_name=name,
            statistic={},
            created_at=datetime.now(),
            last_updated=datetime.now(),
        ))
        session.commit()


# ---------------------------------------------------------------------------
# GET /portfolio/{id}
# ---------------------------------------------------------------------------

class TestGetPortfolio:
    def test_returns_portfolio_with_sections_and_cards(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="My Portfolio")
        sid = _make_section(blank_db, pid)
        _make_block(blank_db, sid)
        _make_card(blank_db, pid, "alpha")

        r = client.get(f"/portfolio/{pid}")
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "My Portfolio"
        assert len(data["sections"]) == 1
        assert len(data["project_cards"]) == 1
        assert data["project_cards"][0]["project_name"] == "alpha"

    def test_returns_404_for_missing_portfolio(self, client, blank_db):
        r = client.get("/portfolio/9999")
        # load_portfolio returns None → response is null body, not 404 by default
        # but the domain layer returns None which FastAPI serialises as null
        # (existing behaviour — just assert no server error)
        assert r.status_code == 200
        assert r.json() is None

    def test_portfolio_mode_is_included(self, client, blank_db):
        pid = _make_portfolio(blank_db, mode="public")
        r = client.get(f"/portfolio/{pid}")
        assert r.status_code == 200
        assert r.json()["metadata"]["mode"] == "public"

    def test_showcase_cards_present_in_response(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "showcase-proj", is_showcase=True)
        _make_card(blank_db, pid, "normal-proj", is_showcase=False)

        r = client.get(f"/portfolio/{pid}")
        cards = r.json()["project_cards"]
        showcase_flags = {c["project_name"]: c["is_showcase"] for c in cards}
        assert showcase_flags["showcase-proj"] is True
        assert showcase_flags["normal-proj"] is False


# ---------------------------------------------------------------------------
# POST /portfolio/generate
# ---------------------------------------------------------------------------

class TestGeneratePortfolio:
    def test_generate_calls_service_and_returns_model(self, client, blank_db):
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.title = "Generated"

        with patch(
            "src.interface.api.routers.portfolio.generate_and_save_portfolio",
            return_value=mock_model,
        ) as mock_gen:
            r = client.post("/portfolio/generate", json={"project_names": ["proj_a"]})

        assert r.status_code == 200
        mock_gen.assert_called_once_with(["proj_a"], None)

    def test_generate_passes_title(self, client, blank_db):
        with patch(
            "src.interface.api.routers.portfolio.generate_and_save_portfolio",
            return_value=MagicMock(),
        ) as mock_gen:
            client.post(
                "/portfolio/generate",
                json={"project_names": ["p1"], "portfolio_title": "Custom Title"},
            )

        mock_gen.assert_called_once_with(["p1"], "Custom Title")

    def test_generate_missing_project_names_returns_422(self, client, blank_db):
        r = client.post("/portfolio/generate", json={})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /portfolio/{id}/refresh
# ---------------------------------------------------------------------------

class TestRefreshPortfolio:
    def test_refresh_calls_update_portfolio(self, client, blank_db):
        pid = _make_portfolio(blank_db)

        with patch(
            "src.interface.api.routers.portfolio.update_portfolio",
            return_value=MagicMock(id=pid),
        ) as mock_refresh:
            r = client.post(f"/portfolio/{pid}/refresh")

        assert r.status_code == 200
        mock_refresh.assert_called_once_with(pid)


# ---------------------------------------------------------------------------
# POST /portfolio/{id}/edit  (new)
# ---------------------------------------------------------------------------

class TestEditPortfolio:
    def test_edit_title(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="Old Title")
        r = client.post(f"/portfolio/{pid}/edit", json={"title": "New Title"})
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

    def test_edit_mode_to_public(self, client, blank_db):
        pid = _make_portfolio(blank_db, mode="private")
        r = client.post(f"/portfolio/{pid}/edit", json={"mode": "public"})
        assert r.status_code == 200
        assert r.json()["mode"] == "public"

    def test_edit_mode_to_private(self, client, blank_db):
        pid = _make_portfolio(blank_db, mode="public")
        r = client.post(f"/portfolio/{pid}/edit", json={"mode": "private"})
        assert r.status_code == 200
        assert r.json()["mode"] == "private"

    def test_edit_invalid_mode_returns_422(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.post(f"/portfolio/{pid}/edit", json={"mode": "readonly"})
        assert r.status_code == 422

    def test_edit_project_ids(self, client, blank_db):
        pid = _make_portfolio(blank_db, project_ids=["a"])
        r = client.post(
            f"/portfolio/{pid}/edit",
            json={"project_ids_include": ["a", "b", "c"]},
        )
        assert r.status_code == 200
        assert set(r.json()["project_ids_include"]) == {"a", "b", "c"}

    def test_edit_missing_portfolio_returns_404(self, client, blank_db):
        r = client.post("/portfolio/9999/edit", json={"title": "x"})
        assert r.status_code == 404

    def test_edit_empty_body_is_noop(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="Unchanged")
        r = client.post(f"/portfolio/{pid}/edit", json={})
        assert r.status_code == 200
        assert r.json()["title"] == "Unchanged"


# ---------------------------------------------------------------------------
# GET /portfolio/{id}/cards  (new)
# ---------------------------------------------------------------------------

class TestGetCards:
    def test_returns_all_cards(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "alpha")
        _make_card(blank_db, pid, "beta")

        r = client.get(f"/portfolio/{pid}/cards")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["portfolio_id"] == pid

    def test_showcase_cards_returned_first(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "zzz-normal")
        _make_card(blank_db, pid, "aaa-showcase", is_showcase=True)

        r = client.get(f"/portfolio/{pid}/cards")
        names = [c["project_name"] for c in r.json()["cards"]]
        assert names[0] == "aaa-showcase"

    def test_filter_by_themes(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "web-proj", themes=["web", "frontend"])
        _make_card(blank_db, pid, "ml-proj", themes=["machine-learning"])

        r = client.get(f"/portfolio/{pid}/cards?themes=web")
        data = r.json()
        assert data["count"] == 1
        assert data["cards"][0]["project_name"] == "web-proj"

    def test_filter_by_tones(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "pro-proj", tones="professional")
        _make_card(blank_db, pid, "exp-proj", tones="experimental")

        r = client.get(f"/portfolio/{pid}/cards?tones=professional")
        data = r.json()
        assert data["count"] == 1
        assert data["cards"][0]["project_name"] == "pro-proj"

    def test_filter_by_tags(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "api-proj", tags=["rest", "api"])
        _make_card(blank_db, pid, "ui-proj", tags=["react", "css"])

        r = client.get(f"/portfolio/{pid}/cards?tags=api")
        data = r.json()
        assert data["count"] == 1
        assert data["cards"][0]["project_name"] == "api-proj"

    def test_filter_by_skills(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "py-proj", skills=["Python", "FastAPI"])
        _make_card(blank_db, pid, "js-proj", skills=["JavaScript", "React"])

        r = client.get(f"/portfolio/{pid}/cards?skills=React")
        data = r.json()
        assert data["count"] == 1
        assert data["cards"][0]["project_name"] == "js-proj"

    def test_filter_multiple_themes_comma_separated(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "web-proj", themes=["web"])
        _make_card(blank_db, pid, "ml-proj", themes=["ml"])
        _make_card(blank_db, pid, "other-proj", themes=["other"])

        r = client.get(f"/portfolio/{pid}/cards?themes=web,ml")
        assert r.json()["count"] == 2

    def test_no_cards_returns_empty(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.get(f"/portfolio/{pid}/cards")
        assert r.json()["count"] == 0
        assert r.json()["cards"] == []

    def test_filter_no_match_returns_empty(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "ml-proj", themes=["ml"])

        r = client.get(f"/portfolio/{pid}/cards?themes=blockchain")
        assert r.json()["count"] == 0

    def test_tags_override_used_for_tag_filter(self, client, blank_db):
        """When tags_override is set, filtering uses it instead of auto tags."""
        pid = _make_portfolio(blank_db)
        with Session(blank_db) as session:
            c = PortfolioProjectCardModel(
                portfolio_id=pid,
                project_name="overridden",
                summary="",
                themes=[],
                tones="",
                tags=["old-tag"],
                skills=[],
                frameworks=[],
                languages={},
                is_showcase=False,
                tags_override=["new-tag", "custom"],
            )
            session.add(c)
            session.commit()

        r = client.get(f"/portfolio/{pid}/cards?tags=new-tag")
        assert r.json()["count"] == 1
        assert r.json()["cards"][0]["project_name"] == "overridden"

        # The old auto tag should NOT match when override is set
        r2 = client.get(f"/portfolio/{pid}/cards?tags=old-tag")
        assert r2.json()["count"] == 0


# ---------------------------------------------------------------------------
# PATCH /portfolio/{id}/cards/{project_name}  (new)
# ---------------------------------------------------------------------------

class TestPatchCard:
    def test_edit_title_override(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj")

        r = client.patch(
            f"/portfolio/{pid}/cards/my-proj",
            json={"title_override": "Custom Title"},
        )
        assert r.status_code == 200
        assert r.json()["title_override"] == "Custom Title"

    def test_edit_summary_override(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj")

        r = client.patch(
            f"/portfolio/{pid}/cards/my-proj",
            json={"summary_override": "My custom summary."},
        )
        assert r.status_code == 200
        assert r.json()["summary_override"] == "My custom summary."

    def test_edit_tags_override(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj")

        r = client.patch(
            f"/portfolio/{pid}/cards/my-proj",
            json={"tags_override": ["rust", "systems"]},
        )
        assert r.status_code == 200
        assert r.json()["tags_override"] == ["rust", "systems"]

    def test_edit_sets_last_user_edit_at(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj")

        r = client.patch(
            f"/portfolio/{pid}/cards/my-proj",
            json={"title_override": "x"},
        )
        assert r.status_code == 200
        assert r.json()["last_user_edit_at"] is not None

    def test_auto_fields_not_changed_by_edit(self, client, blank_db):
        """Editing overrides does not affect auto-populated fields like summary."""
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj", summary="Original summary")

        r = client.patch(
            f"/portfolio/{pid}/cards/my-proj",
            json={"title_override": "New title"},
        )
        assert r.status_code == 200
        assert r.json()["summary"] == "Original summary"

    def test_empty_patch_still_sets_edit_timestamp(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "my-proj")

        r = client.patch(f"/portfolio/{pid}/cards/my-proj", json={})
        assert r.status_code == 200
        # last_user_edit_at gets set even on empty patch
        assert r.json()["last_user_edit_at"] is not None

    def test_patch_missing_card_returns_404(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.patch(
            f"/portfolio/{pid}/cards/nonexistent-proj",
            json={"title_override": "x"},
        )
        assert r.status_code == 404

    def test_patch_wrong_portfolio_returns_404(self, client, blank_db):
        pid1 = _make_portfolio(blank_db)
        pid2 = _make_portfolio(blank_db)
        _make_card(blank_db, pid1, "proj-a")

        r = client.patch(
            f"/portfolio/{pid2}/cards/proj-a",
            json={"title_override": "x"},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /portfolio/{id}/cards/{project_name}/showcase  (new)
# ---------------------------------------------------------------------------

class TestShowcaseToggle:
    def test_set_showcase_true(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "proj", is_showcase=False)

        r = client.post(
            f"/portfolio/{pid}/cards/proj/showcase",
            json={"is_showcase": True},
        )
        assert r.status_code == 200
        assert r.json()["is_showcase"] is True

    def test_set_showcase_false(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "proj", is_showcase=True)

        r = client.post(
            f"/portfolio/{pid}/cards/proj/showcase",
            json={"is_showcase": False},
        )
        assert r.status_code == 200
        assert r.json()["is_showcase"] is False

    def test_showcase_toggle_does_not_touch_other_fields(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "proj", summary="Keep this summary", is_showcase=False)

        r = client.post(
            f"/portfolio/{pid}/cards/proj/showcase",
            json={"is_showcase": True},
        )
        assert r.status_code == 200
        assert r.json()["summary"] == "Keep this summary"

    def test_showcase_toggle_missing_card_returns_404(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.post(
            f"/portfolio/{pid}/cards/ghost/showcase",
            json={"is_showcase": True},
        )
        assert r.status_code == 404

    def test_showcase_flag_survives_subsequent_card_edit(self, client, blank_db):
        """Editing card overrides must not clear the showcase flag."""
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "proj", is_showcase=True)

        client.patch(
            f"/portfolio/{pid}/cards/proj",
            json={"title_override": "New title"},
        )

        r = client.get(f"/portfolio/{pid}/cards")
        cards = r.json()["cards"]
        assert cards[0]["is_showcase"] is True

    def test_multiple_projects_can_be_showcased(self, client, blank_db):
        """No cap on the number of showcase projects."""
        pid = _make_portfolio(blank_db)
        for name in ["p1", "p2", "p3", "p4", "p5"]:
            _make_card(blank_db, pid, name)
            client.post(
                f"/portfolio/{pid}/cards/{name}/showcase",
                json={"is_showcase": True},
            )

        r = client.get(f"/portfolio/{pid}/cards")
        showcased = [c for c in r.json()["cards"] if c["is_showcase"]]
        assert len(showcased) == 5


# ---------------------------------------------------------------------------
# GET /portfolio/{id}/export  (new)
# ---------------------------------------------------------------------------

class TestExportPortfolio:
    def test_export_returns_zip(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="Export Test")
        _make_card(blank_db, pid, "proj-a", is_showcase=True)
        _make_card(blank_db, pid, "proj-b")

        r = client.get(f"/portfolio/{pid}/export")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        assert "attachment" in r.headers["content-disposition"]
        assert f"portfolio_{pid}.zip" in r.headers["content-disposition"]

    def test_export_zip_contains_required_files(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.get(f"/portfolio/{pid}/export")

        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "index.html" in names
        assert "portfolio_data.js" in names
        assert "style.css" in names
        assert "filter.js" in names

    def test_export_portfolio_data_contains_cards(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="Data Test")
        _make_card(blank_db, pid, "alpha", themes=["web"], is_showcase=True)
        _make_card(blank_db, pid, "beta", themes=["ml"])

        r = client.get(f"/portfolio/{pid}/export")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        js_src = zf.read("portfolio_data.js").decode("utf-8")

        # portfolio_data.js must declare the PORTFOLIO_DATA variable
        assert "PORTFOLIO_DATA" in js_src

        # Parse the JSON out of the JS assignment
        json_str = js_src.replace("var PORTFOLIO_DATA = ", "").rstrip(";\n")
        data = json.loads(json_str)

        assert data["title"] == "Data Test"
        assert data["portfolio_id"] == pid
        card_names = {c["project_name"] for c in data["project_cards"]}
        assert card_names == {"alpha", "beta"}

    def test_export_showcase_cards_flagged_in_data(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_card(blank_db, pid, "showcase-proj", is_showcase=True)
        _make_card(blank_db, pid, "normal-proj", is_showcase=False)

        r = client.get(f"/portfolio/{pid}/export")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        js_src = zf.read("portfolio_data.js").decode("utf-8")
        json_str = js_src.replace("var PORTFOLIO_DATA = ", "").rstrip(";\n")
        data = json.loads(json_str)

        showcase_flags = {c["project_name"]: c["is_showcase"] for c in data["project_cards"]}
        assert showcase_flags["showcase-proj"] is True
        assert showcase_flags["normal-proj"] is False

    def test_export_index_html_contains_title(self, client, blank_db):
        pid = _make_portfolio(blank_db, title="My Amazing Portfolio")
        r = client.get(f"/portfolio/{pid}/export")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        html = zf.read("index.html").decode("utf-8")
        assert "My Amazing Portfolio" in html

    def test_export_filter_js_is_non_empty(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        r = client.get(f"/portfolio/{pid}/export")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert len(zf.read("filter.js")) > 100

    def test_export_missing_portfolio_returns_404(self, client, blank_db):
        r = client.get("/portfolio/9999/export")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /portfolio/{id}/sections/{section_id}/block/{block_tag}/edit
# ---------------------------------------------------------------------------

class TestEditBlock:
    def test_edit_text_block(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        sid = _make_section(blank_db, pid, section_id="summary")
        _make_block(blank_db, sid, tag="main_block", content="Old text")

        r = client.post(
            f"/portfolio/{pid}/sections/summary/block/main_block/edit",
            json={"text": "New text"},
        )
        assert r.status_code == 200
        # Verify the change persisted — read back via GET /portfolio
        r2 = client.get(f"/portfolio/{pid}")
        section = r2.json()["sections"][0]
        block = section["blocks_by_tag"]["main_block"]
        # TextBlock serialises as {"content_type": "Text", "text": "<value>"}
        assert block["current_content"]["text"] == "New text"

    def test_edit_missing_block_returns_404(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_section(blank_db, pid, section_id="summary")

        r = client.post(
            f"/portfolio/{pid}/sections/summary/block/ghost_block/edit",
            json={"text": "x"},
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /portfolio/{id}/conflicts
# ---------------------------------------------------------------------------

class TestListConflicts:
    def test_no_conflicts_returns_empty(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        sid = _make_section(blank_db, pid)
        _make_block(blank_db, sid, in_conflict=False)

        r = client.get(f"/portfolio/{pid}/conflicts")
        assert r.status_code == 200
        assert r.json() == []

    def test_conflict_block_is_listed(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        sid = _make_section(blank_db, pid, section_id="summary")
        _make_block(
            blank_db, sid,
            tag="conflict_block",
            content="user version",
            in_conflict=True,
            conflict_content="system version",
        )

        r = client.get(f"/portfolio/{pid}/conflicts")
        assert r.status_code == 200
        conflicts = r.json()
        assert len(conflicts) == 1
        assert conflicts[0]["block_tag"] == "conflict_block"
        assert conflicts[0]["section_tag"] == "summary"
        assert conflicts[0]["current_content"] == "user version"
        assert conflicts[0]["conflicting_content"] == "system version"


# ---------------------------------------------------------------------------
# POST /portfolio/{id}/sections/{section_id}/blocks/{block_tag}/resolve-accept
# ---------------------------------------------------------------------------

class TestResolveConflict:
    def test_resolve_accept_system_clears_conflict(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        sid = _make_section(blank_db, pid, section_id="summary")
        _make_block(
            blank_db, sid,
            tag="main_block",
            content="user version",
            in_conflict=True,
            conflict_content="system version",
        )

        r = client.post(
            f"/portfolio/{pid}/sections/summary/blocks/main_block/resolve-accept"
        )
        assert r.status_code == 200
        result = r.json()
        assert result["in_conflict"] is False
        assert result["current_content"] == "system version"

    def test_resolve_nonexistent_block_returns_404(self, client, blank_db):
        pid = _make_portfolio(blank_db)
        _make_section(blank_db, pid, section_id="summary")

        r = client.post(
            f"/portfolio/{pid}/sections/summary/blocks/ghost/resolve-accept"
        )
        assert r.status_code == 404
