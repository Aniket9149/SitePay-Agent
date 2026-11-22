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
    dependencies = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())["project"][
        "dependencies"
    ]
    assert any(dependency.startswith("psycopg") for dependency in dependencies)


def test_ci_workflow_runs_every_required_check_in_independent_jobs() -> None:
    """Rules, lint, tests, the server smoke test and the migrations run as separate jobs."""
    workflow = load_yaml(".github/workflows/continuous_integration.yml")
    jobs = workflow["jobs"]
    assert set(jobs) == {"rules", "lint", "tests", "smoke", "migrations"}
    for job in jobs.values():
        assert "needs" not in job, "a failing job must not hide the result of another"

    def commands(job_name: str) -> str:
        """Join the shell commands of one job so a test can search them.

        Steps that only use an action have no command.
        """
        return " ".join(step.get("run", "") for step in jobs[job_name]["steps"])

    assert "scripts/check_project_rules.py" in commands("rules")
    assert "ruff check" in commands("lint")
    assert "pytest" in commands("tests")
    assert "scripts/smoke_test_backend.py" in commands("smoke")
    assert "scripts/check_migrations.py" in commands("migrations")
    assert jobs["tests"]["env"]["SITEPAY_REQUIRE_FULL_STACK"] == "1"
    assert jobs["migrations"]["strategy"]["matrix"]["database"] == ["sqlite", "postgresql"]


def test_pyproject_has_required_runtime_dependencies() -> None:
    """The planned stack is listed, and Python 3.12 or later is required."""
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())["project"]
    names = {
        dependency.split(">")[0].split("[")[0].strip() for dependency in project["dependencies"]
    }
    assert {"fastapi", "sqlalchemy", "alembic", "pydantic", "pyjwt"} <= names
    assert project["requires-python"] == ">=3.12"
