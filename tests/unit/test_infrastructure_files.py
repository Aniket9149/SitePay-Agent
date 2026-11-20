#Owner::ANIKET::ANHOTRA = MR.Panda
"""Checks that the compose file, CI workflow and project config parse and follow the rules.

These prove the files are valid and contain no hard coded secrets. They do not prove
that Docker or GitHub Actions run them successfully.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(relative_path: str) -> dict[Any, Any]:
    """Load a YAML file under the project root into a dictionary.

    Raises if the file is not valid YAML, which fails the test.
    """
    loaded = yaml.safe_load((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_compose_defines_database_and_backend_without_hard_coded_secrets() -> None:
    """Secrets in the compose file must come from environment variables."""
    compose = load_yaml("docker-compose.yml")
    assert set(compose["services"]) == {"database", "backend"}
    for service in compose["services"].values():
        for key, value in (service.get("environment") or {}).items():
            if "PASSWORD" in key or "SECRET" in key:
                assert str(value).startswith("${"), key
    backend_command = compose["services"]["backend"]["command"]
    assert "alembic upgrade head" in backend_command
    assert "--factory" in backend_command


def test_compose_database_url_matches_the_supported_driver() -> None:
    """The backend uses the psycopg driver, which the project depends on."""
    compose = load_yaml("docker-compose.yml")
    database_url = compose["services"]["backend"]["environment"]["DATABASE_URL"]
    assert database_url.startswith("postgresql+psycopg://")
    dependencies = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    assert any(dependency.startswith("psycopg") for dependency in dependencies)


def test_ci_workflow_runs_rules_lint_and_tests() -> None:
    """The continuous integration job runs every required check."""
    workflow = load_yaml(".github/workflows/continuous_integration.yml")
    steps = workflow["jobs"]["checks"]["steps"]
    commands = " ".join(step.get("run", "") for step in steps)
    assert "scripts/check_project_rules.py" in commands
    assert "ruff check" in commands
    assert "pytest" in commands


def test_pyproject_has_required_runtime_dependencies() -> None:
    """The planned stack is listed, and Python 3.12 or later is required."""
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())["project"]
    names = {
        dependency.split(">")[0].split("[")[0].strip() for dependency in project["dependencies"]
    }
    assert {"fastapi", "sqlalchemy", "alembic", "pydantic", "pyjwt"} <= names
    assert project["requires-python"] == ">=3.12"
