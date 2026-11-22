#Owner::ANIKET::ANHOTRA = MR.Panda
"""Tests for the project rule checker, covering each rule and the command line."""

from __future__ import annotations

from pathlib import Path

import pytest

import check_project_rules as checker

OWNER_TAG = "#Owner::ANIKET::ANHOTRA = MR.Panda"
EM_DASH = chr(0x2014)


def write_file(directory: Path, relative_name: str, content: str) -> Path:
    """Create a file under the directory with the content and return its path.

    Parent folders are created when needed.
    """
    file_path = directory / relative_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def rule_names(violations: list[checker.RuleViolation]) -> list[str]:
    """Return the rule name of each violation in order.

    Used to keep assertions short and readable.
    """
    return [violation.rule_name for violation in violations]


def test_valid_python_file_has_no_violations(tmp_path: Path) -> None:
    """A python file with the tag first and no em dash passes cleanly."""
    write_file(tmp_path, "good.py", OWNER_TAG + "\nvalue = 1\n")
    assert checker.scan_project(tmp_path) == []


def test_missing_owner_tag_is_reported(tmp_path: Path) -> None:
    """A python file without the tag on line one fails the owner tag rule."""
    write_file(tmp_path, "bad.py", "value = 1\n")
    assert rule_names(checker.scan_project(tmp_path)) == ["owner-tag"]


def test_tag_not_on_first_line_is_reported(tmp_path: Path) -> None:
    """The tag on line two is still a violation because it must be first."""
    write_file(tmp_path, "late.py", "import os\n" + OWNER_TAG + "\n")
    assert rule_names(checker.scan_project(tmp_path)) == ["owner-tag"]


def test_tag_with_wrong_text_is_reported(tmp_path: Path) -> None:
    """A near miss of the tag text must not pass."""
    write_file(tmp_path, "typo.py", "#Owner::ANIKET::ANHOTRA = MR.panda\n")
    assert rule_names(checker.scan_project(tmp_path)) == ["owner-tag"]


def test_empty_code_file_is_reported(tmp_path: Path) -> None:
    """An empty code file has no tag, so it fails the owner tag rule."""
    write_file(tmp_path, "empty.py", "")
    assert rule_names(checker.scan_project(tmp_path)) == ["owner-tag"]


def test_typescript_uses_slash_comment_form(tmp_path: Path) -> None:
    """TypeScript accepts the slash comment form and rejects the bare hash form."""
    write_file(tmp_path, "ok.ts", "// " + OWNER_TAG + "\nexport const a = 1;\n")
    write_file(tmp_path, "bad.ts", OWNER_TAG + "\nexport const a = 1;\n")
    flagged = {violation.file_path.name for violation in checker.scan_project(tmp_path)}
    assert flagged == {"bad.ts"}


def test_css_uses_block_comment_form(tmp_path: Path) -> None:
    """CSS requires the block comment form of the tag."""
    write_file(tmp_path, "ok.css", "/* " + OWNER_TAG + " */\nbody {}\n")
    write_file(tmp_path, "bad.css", "// " + OWNER_TAG + "\nbody {}\n")
    flagged = {violation.file_path.name for violation in checker.scan_project(tmp_path)}
    assert flagged == {"bad.css"}


def test_em_dash_reported_with_line_number(tmp_path: Path) -> None:
    """An em dash in a markdown file is reported on the correct line."""
    write_file(tmp_path, "notes.md", "fine line\nbad " + EM_DASH + " line\n")
    violations = checker.scan_project(tmp_path)
    assert rule_names(violations) == ["em-dash"]
    assert violations[0].line_number == 2


def test_plain_hyphen_and_en_dash_are_allowed(tmp_path: Path) -> None:
    """Only the em dash is banned, plain hyphens pass."""
    write_file(tmp_path, "notes.md", "well-known item - fine\n")
    assert checker.scan_project(tmp_path) == []


def test_file_at_limit_passes_and_over_limit_fails(tmp_path: Path) -> None:
    """Exactly 300 lines passes and 301 lines fails the length rule."""
    at_limit = OWNER_TAG + "\n" + "x = 1\n" * 299
    over_limit = OWNER_TAG + "\n" + "x = 1\n" * 300
    write_file(tmp_path, "at_limit.py", at_limit)
    write_file(tmp_path, "over_limit.py", over_limit)
    flagged = {violation.file_path.name for violation in checker.scan_project(tmp_path)}
    assert flagged == {"over_limit.py"}


def test_documents_are_not_limited_by_line_count(tmp_path: Path) -> None:
    """The length rule applies to code files only, long documents are allowed."""
    write_file(tmp_path, "long.md", "line\n" * 500)
    assert checker.scan_project(tmp_path) == []


def test_excluded_directories_are_skipped(tmp_path: Path) -> None:
    """Files inside generated or vendor folders are never scanned."""
    write_file(tmp_path, "node_modules/pkg/index.js", "no tag " + EM_DASH + "\n")
    write_file(tmp_path, ".venv/lib/mod.py", "no tag\n")
    assert checker.scan_project(tmp_path) == []


def test_binary_and_unknown_files_are_skipped(tmp_path: Path) -> None:
    """Unknown extensions and undecodable files do not crash or fail the check."""
    (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8\xff" + EM_DASH.encode("utf-8"))
    (tmp_path / "broken.md").write_bytes(b"\xff\xfe\x00bad")
    assert checker.scan_project(tmp_path) == []


def test_exact_file_names_without_extension_are_scanned(tmp_path: Path) -> None:
    """Makefile and similar named files are scanned for em dashes."""
    write_file(tmp_path, "Makefile", "target: " + EM_DASH + "\n")
    assert rule_names(checker.scan_project(tmp_path)) == ["em-dash"]


def test_multiple_rules_on_one_file_are_all_reported(tmp_path: Path) -> None:
    """A file can break both the em dash and owner tag rules at once."""
    write_file(tmp_path, "both.py", "x = '" + EM_DASH + "'\n")
    assert sorted(rule_names(checker.scan_project(tmp_path))) == ["em-dash", "owner-tag"]


def test_main_returns_zero_when_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The command line exits with 0 and reports the scanned count."""
    write_file(tmp_path, "good.py", OWNER_TAG + "\n")
    assert checker.main([str(tmp_path)]) == 0
    assert "found 0 violations" in capsys.readouterr().out


def test_main_returns_one_when_violations_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command line exits with 1 and prints each violation."""
    write_file(tmp_path, "bad.py", "x = 1\n")
    assert checker.main([str(tmp_path)]) == 1
    assert "[owner-tag]" in capsys.readouterr().out
