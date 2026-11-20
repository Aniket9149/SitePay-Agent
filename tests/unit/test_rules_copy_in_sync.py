#Owner::ANIKET::ANHOTRA = MR.Panda
"""Test that the rules copy in docs stays identical to the master rules file."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_docs_rules_copy_matches_project_rules() -> None:
    """docs/03_rules.md must be an exact copy of PROJECT_RULES.md.

    If this fails, copy PROJECT_RULES.md over docs/03_rules.md.
    """
    master_text = (PROJECT_ROOT / "PROJECT_RULES.md").read_text(encoding="utf-8")
    copy_text = (PROJECT_ROOT / "docs" / "03_rules.md").read_text(encoding="utf-8")
    assert master_text == copy_text
