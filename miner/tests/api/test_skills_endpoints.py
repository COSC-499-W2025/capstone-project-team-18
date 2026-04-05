"""
Tests for GET /skills
"""
from unittest.mock import patch, MagicMock


def _make_skill(name: str, weight: float):
    s = MagicMock()
    s.skill_name = name
    s.weight = weight
    return s


class TestGetSkills:
    def test_returns_200_with_skills_key(self, client, blank_db):
        with patch('src.interface.api.routers.skills.get_skills') as mock_gs:
            mock_gs.return_value = []
            r = client.get("/skills")
        assert r.status_code == 200
        assert "skills" in r.json()

    def test_empty_when_no_projects(self, client, blank_db):
        with patch('src.interface.api.routers.skills.get_skills') as mock_gs:
            mock_gs.return_value = []
            r = client.get("/skills")
        assert r.json()["skills"] == []

    def test_returns_skills_with_name_and_weight(self, client, blank_db):
        with patch('src.interface.api.routers.skills.get_skills') as mock_gs:
            mock_gs.return_value = [
                _make_skill("Python", 0.9),
                _make_skill("JavaScript", 0.6),
            ]
            r = client.get("/skills")
        skills = r.json()["skills"]
        assert len(skills) == 2
        names = {s["name"] for s in skills}
        assert names == {"Python", "JavaScript"}

    def test_skill_weight_is_float(self, client, blank_db):
        with patch('src.interface.api.routers.skills.get_skills') as mock_gs:
            mock_gs.return_value = [_make_skill("Go", 0.75)]
            r = client.get("/skills")
        skill = r.json()["skills"][0]
        assert isinstance(skill["weight"], float)
        assert skill["weight"] == 0.75

    def test_response_fields_are_name_and_weight(self, client, blank_db):
        with patch('src.interface.api.routers.skills.get_skills') as mock_gs:
            mock_gs.return_value = [_make_skill("Rust", 0.5)]
            r = client.get("/skills")
        skill = r.json()["skills"][0]
        assert set(skill.keys()) == {"name", "weight"}
