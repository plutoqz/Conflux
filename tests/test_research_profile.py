import subprocess
import sys
from pathlib import Path

import pytest


def test_load_valid_profile():
    from conflux.research_profile import load_profile

    profile = load_profile("profiles/example_gis_agent.yaml")

    assert profile.id == "gis-agent-research"
    assert "geospatial data fusion" in profile.keywords
    assert profile.report_cadence == "weekly"
    assert not profile.warnings


def test_missing_required_field_fails(tmp_path):
    from conflux.research_profile import ProfileValidationError, load_profile

    path = tmp_path / "bad.yaml"
    path.write_text(
        """
id: bad-profile
fields:
  - GIS
research_questions:
  - What changed?
keywords:
  - GIS
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError, match="name is required"):
        load_profile(path)


def test_empty_research_questions_fail(tmp_path):
    from conflux.research_profile import ProfileValidationError, load_profile

    path = tmp_path / "empty-questions.yaml"
    path.write_text(
        """
id: empty-questions
name: Empty Questions
fields:
  - GIS
research_questions: []
keywords:
  - GIS
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError, match="research_questions"):
        load_profile(path)


def test_nonexistent_paths_warn_without_failing(tmp_path):
    from conflux.research_profile import load_profile

    path = tmp_path / "warn.yaml"
    path.write_text(
        """
id: warning-profile
name: Warning Profile
fields:
  - GIS
research_questions:
  - What should be audited?
keywords:
  - GIS
project_paths:
  - missing-project
document_paths:
  - missing-docs
""".strip(),
        encoding="utf-8",
    )

    profile = load_profile(path)

    assert len(profile.warnings) == 2
    assert all("path does not exist" in warning for warning in profile.warnings)


def test_academy_hunter_profile_can_be_mapped():
    from conflux.research_profile import profile_from_academy_hunter, validate_profile

    payload = {
        "profile": {"name": "Fusion Agent Research", "thesis_short": "GIS agent workflow"},
        "tracks": [
            {
                "id": "llm_agent",
                "name": "LLM Agent",
                "description": "Planning and tool use",
                "queries": [
                    {
                        "keywords": "LLM agent OR language model agent",
                        "suffix": "planning OR workflow",
                        "categories": ["cs.AI", "cs.CL"],
                    }
                ],
                "venues_priority": ["NeurIPS", "ICLR"],
            }
        ],
        "negative_filters": {
            "title_exclude_any": [["clinical", "stock market"]],
            "abstract_exclude": ["drug discovery"],
        },
        "research_questions": {
            "RQ1": {
                "question": "Can agents improve geospatial workflow planning?",
                "key_terms": ["workflow validation", "agent planning"],
            }
        },
        "scholars_to_watch": ["Krzysztof Janowicz"],
    }

    profile = validate_profile(profile_from_academy_hunter(payload))

    assert profile.id == "fusion-agent-research"
    assert profile.research_questions == ["Can agents improve geospatial workflow planning?"]
    assert "LLM agent OR language model agent" in profile.keywords
    assert "drug discovery" in profile.negative_keywords
    assert "Krzysztof Janowicz" in profile.tracked_scholars


def test_profile_cli_validate_and_show():
    root = Path(__file__).resolve().parents[1]

    validate_result = subprocess.run(
        [sys.executable, "-m", "conflux.research_profile.cli", "validate", "profiles/example_gis_agent.yaml"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate_result.returncode == 0, validate_result.stderr
    assert "Profile OK: gis-agent-research" in validate_result.stdout

    show_result = subprocess.run(
        [sys.executable, "-m", "conflux.research_profile.cli", "show", "profiles/example_gis_agent.yaml", "--json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert show_result.returncode == 0, show_result.stderr
    assert '"id": "gis-agent-research"' in show_result.stdout
