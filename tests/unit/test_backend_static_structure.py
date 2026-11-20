#Owner::ANIKET::ANHOTRA = MR.Panda
"""Static structure checks on backend code that cannot be executed without its framework.

These use Python's own parser, so they run anywhere. They prove structure only (the code
compiles, models match the migration, rules B5 hold). They do NOT prove the code runs.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
APP_ROOT = BACKEND_ROOT / "app"
MIGRATION_PATH = BACKEND_ROOT / "migrations" / "versions" / "0001_create_core_and_audit_tables.py"
COMMON_COLUMNS = {"id", "created_at", "updated_at"}
FRAMEWORK_FREE_MODULES = [
    "errors.py", "config.py", "logging_setup.py", "feature_flags.py", "database_triggers.py",
    "security/password_hasher.py", "security/token_service.py", "security/permissions.py",
    "security/audit_hash.py", "schemas/auth_schema.py", "schemas/organization_schema.py",
    "schemas/project_schema.py", "contracts/__init__.py", "contracts/entity_references.py",
    "contracts/review_states.py", "contracts/audit_actions.py",
    "contracts/quantities_and_money.py", "contracts/pagination.py",
]
FORBIDDEN_IN_FRAMEWORK_FREE = {"sqlalchemy", "fastapi", "alembic", "starlette"}


def backend_python_files() -> list[Path]:
    """List every Python file under the backend folder, sorted.

    Cache folders are skipped.
    """
    return sorted(
        path for path in BACKEND_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def parse(path: Path) -> ast.Module:
    """Parse a source file into a syntax tree.

    Raises SyntaxError, which fails the test, if the file does not compile.
    """
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_top_level_names(tree: ast.Module) -> set[str]:
    """Return the top level package names a module imports.

    Used to prove a module does not depend on a framework.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def model_tables() -> dict[str, set[str]]:
    """Read table names and column names from the model classes, without importing them.

    Columns inherited from IdentifiedTimestampedModel are added automatically.
    """
    tables: dict[str, set[str]] = {}
    for path in sorted((APP_ROOT / "models").glob("*_model.py")):
        for node in parse(path).body:
            if not isinstance(node, ast.ClassDef):
                continue
            table_name = None
            columns: set[str] = set()
            for statement in node.body:
                if (
                    isinstance(statement, ast.Assign)
                    and isinstance(statement.targets[0], ast.Name)
                    and statement.targets[0].id == "__tablename__"
                    and isinstance(statement.value, ast.Constant)
                ):
                    table_name = str(statement.value.value)
                elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                    columns.add(statement.target.id)
            if table_name is not None:
                base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
                if "IdentifiedTimestampedModel" in base_names:
                    columns |= COMMON_COLUMNS
                tables[table_name] = columns
    return tables


def migration_tables() -> dict[str, set[str]]:
    """Read table names and column names from the create_table calls in migration 0001.

    The shared timestamp helper is expanded to its two columns.
    """
    tables: dict[str, set[str]] = {}
    for node in ast.walk(parse(MIGRATION_PATH)):
        is_create_table = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create_table"
        )
        if not is_create_table:
            continue
        assert isinstance(node, ast.Call)
        table_name = str(node.args[0].value)  # type: ignore[attr-defined]
        columns: set[str] = set()
        for argument in node.args[1:]:
            if isinstance(argument, ast.Starred):
                columns |= {"created_at", "updated_at"}
            elif (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Attribute)
                and argument.func.attr == "Column"
            ):
                columns.add(str(argument.args[0].value))  # type: ignore[attr-defined]
        tables[table_name] = columns
    return tables


@pytest.mark.parametrize("path", backend_python_files(), ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_every_backend_file_compiles(path: Path) -> None:
    """Every backend file is valid Python for this interpreter."""
    compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_every_app_function_has_docstring_and_type_hints() -> None:
    """Rule B5: each function declares input and output types and has a description."""
    problems: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        for node in ast.walk(parse(path)):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            label = f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} {node.name}"
            if ast.get_docstring(node) is None:
                problems.append(label + " has no docstring")
            if node.returns is None:
                problems.append(label + " has no return type")
            every_argument = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            for argument in every_argument:
                if argument.arg not in ("self", "cls") and argument.annotation is None:
                    problems.append(f"{label} argument {argument.arg} has no type")
    assert problems == []


def test_models_match_migration_tables_and_columns() -> None:
    """Every model table exists in the migration with exactly the same columns."""
    models, migration = model_tables(), migration_tables()
    assert set(models) == set(migration) == {
        "users", "organizations", "memberships", "projects", "sites", "refresh_tokens", "audit_logs",
    }
    for table_name, model_columns in models.items():
        assert model_columns == migration[table_name], table_name


def test_literal_constraint_and_index_names_appear_in_migration() -> None:
    """Names written explicitly in models are also created by the migration."""
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    missing: list[str] = []
    for path in (APP_ROOT / "models").glob("*_model.py"):
        tree = parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if value.startswith(("uq_", "ix_")) and value not in migration_text:
                    missing.append(value)
    assert missing == []


def test_framework_free_modules_do_not_import_frameworks() -> None:
    """Pure modules stay testable anywhere because they import no web or database framework."""
    offenders = {
        relative: sorted(imported_top_level_names(parse(APP_ROOT / relative)) & FORBIDDEN_IN_FRAMEWORK_FREE)
        for relative in FRAMEWORK_FREE_MODULES
    }
    assert {name: found for name, found in offenders.items() if found} == {}


def test_services_do_not_import_the_web_framework() -> None:
    """Business services must not depend on FastAPI, so they can be reused by workers."""
    for path in (APP_ROOT / "services").glob("*.py"):
        assert "fastapi" not in imported_top_level_names(parse(path)), path.name


def test_money_code_never_uses_float() -> None:
    """Rule F2: no floating point type is used for money in models or project formats."""
    watched = list((APP_ROOT / "models").glob("*.py")) + [APP_ROOT / "schemas" / "project_schema.py"]
    for path in watched:
        names = {node.id for node in ast.walk(parse(path)) if isinstance(node, ast.Name)}
        assert "float" not in names, path.name


def test_every_route_module_is_registered_in_main() -> None:
    """Each api module defines a router and main.py includes it."""
    main_text = (APP_ROOT / "main.py").read_text(encoding="utf-8")
    for path in sorted((APP_ROOT / "api").glob("*_routes.py")):
        assert "router = APIRouter(" in path.read_text(encoding="utf-8"), path.name
        assert f"{path.stem}.router" in main_text, path.name


def test_every_mutating_route_commits_exactly_when_it_changes_data() -> None:
    """Routes that create, change or delete data call session.commit()."""
    for path in sorted((APP_ROOT / "api").glob("*_routes.py")):
        for node in ast.walk(parse(path)):
            if not isinstance(node, ast.FunctionDef):
                continue
            methods = {
                decorator.func.attr
                for decorator in node.decorator_list
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
            }
            source = ast.unparse(node)
            if methods & {"post", "patch", "delete"}:
                assert "session.commit()" in source, f"{path.name}:{node.name}"
            if methods == {"get"}:
                assert "session.commit()" not in source, f"{path.name}:{node.name}"


def test_migration_has_one_revision_with_up_and_down() -> None:
    """Migration 0001 is the single head and can be rolled back."""
    tree = parse(MIGRATION_PATH)
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert ast.literal_eval(assignments["revision"]) == "0001"
    assert ast.literal_eval(assignments["down_revision"]) is None
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"upgrade", "downgrade"} <= function_names
