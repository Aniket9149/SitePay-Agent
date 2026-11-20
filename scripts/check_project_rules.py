#Owner::ANIKET::ANHOTRA = MR.Panda
"""Automatic project rule checker for SitePay Agent.

Checks three mandatory rules on every file: the owner tag on the first line
of each code file, the absence of em dashes in every text file, and the
300 line limit on each code file. Exit code 0 means clean, 1 means violations.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

OWNER_TAG_TEXT = "#Owner::ANIKET::ANHOTRA = MR.Panda"
EM_DASH_CHARACTER = chr(0x2014)
MAXIMUM_CODE_FILE_LINES = 300

# Expected first line per code file extension. Languages where the hash symbol
# is not a comment use their own comment syntax with the same tag text.
EXPECTED_FIRST_LINE_BY_EXTENSION: dict[str, str] = {
    ".py": OWNER_TAG_TEXT,
    ".sh": OWNER_TAG_TEXT,
    ".yml": OWNER_TAG_TEXT,
    ".yaml": OWNER_TAG_TEXT,
    ".ts": "// " + OWNER_TAG_TEXT,
    ".tsx": "// " + OWNER_TAG_TEXT,
    ".js": "// " + OWNER_TAG_TEXT,
    ".css": "/* " + OWNER_TAG_TEXT + " */",
}

TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py", ".sh", ".yml", ".yaml", ".ts", ".tsx", ".js", ".css", ".html",
        ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".sql",
    }
)
TEXT_FILE_NAMES: frozenset[str] = frozenset(
    {"Makefile", "LICENSE", ".gitignore", ".editorconfig", ".env.example"}
)
EXCLUDED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
     ".ruff_cache", "dist", "build", ".mypy_cache"}
)


@dataclass(frozen=True)
class RuleViolation:
    """One broken rule, with the file, line number and a plain message."""

    file_path: Path
    line_number: int
    rule_name: str
    message: str

    def format_for_display(self) -> str:
        """Return the violation as a single readable line for terminal output."""
        return f"{self.file_path}:{self.line_number}: [{self.rule_name}] {self.message}"


def is_text_file(file_path: Path) -> bool:
    """Return True when the file is a known text type that must be scanned.

    Matching uses the extension or the exact file name.
    """
    return file_path.suffix in TEXT_EXTENSIONS or file_path.name in TEXT_FILE_NAMES


def is_code_file(file_path: Path) -> bool:
    """Return True when the file is a code file that needs the owner tag.

    Code files are the extensions listed in the expected first line table.
    """
    return file_path.suffix in EXPECTED_FIRST_LINE_BY_EXTENSION


def check_owner_tag(file_path: Path, file_lines: list[str]) -> list[RuleViolation]:
    """Check that the first line of a code file is exactly the owner tag.

    Returns an empty list when correct, otherwise one violation on line 1.
    """
    expected_line = EXPECTED_FIRST_LINE_BY_EXTENSION[file_path.suffix]
    actual_line = file_lines[0].rstrip("\r\n") if file_lines else ""
    if actual_line == expected_line:
        return []
    return [
        RuleViolation(
            file_path, 1, "owner-tag",
            f"first line must be exactly: {expected_line}",
        )
    ]


def check_em_dash(file_path: Path, file_lines: list[str]) -> list[RuleViolation]:
    """Find every line that contains an em dash character.

    Returns one violation per offending line, numbered from 1.
    """
    return [
        RuleViolation(file_path, line_number, "em-dash",
                      "em dash found, use a comma, full stop or plain hyphen")
        for line_number, line_text in enumerate(file_lines, start=1)
        if EM_DASH_CHARACTER in line_text
    ]


def check_file_length(file_path: Path, file_lines: list[str]) -> list[RuleViolation]:
    """Check that a code file stays within the maximum allowed line count.

    Returns one violation on the first line over the limit, or none.
    """
    if len(file_lines) <= MAXIMUM_CODE_FILE_LINES:
        return []
    return [
        RuleViolation(
            file_path, MAXIMUM_CODE_FILE_LINES + 1, "file-length",
            f"{len(file_lines)} lines, limit is {MAXIMUM_CODE_FILE_LINES}, split the file",
        )
    ]


def check_single_file(file_path: Path) -> list[RuleViolation]:
    """Run every applicable rule on one file and return all violations.

    Files that are not text, or cannot be decoded as UTF-8, are skipped.
    """
    if not is_text_file(file_path):
        return []
    try:
        file_lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return []
    violations = check_em_dash(file_path, file_lines)
    if is_code_file(file_path):
        violations += check_owner_tag(file_path, file_lines)
        violations += check_file_length(file_path, file_lines)
    return violations


def iterate_project_files(root_directory: Path) -> list[Path]:
    """List every file under the root, skipping generated and vendor folders.

    The result is sorted so reports are stable between runs.
    """
    return sorted(
        candidate
        for candidate in root_directory.rglob("*")
        if candidate.is_file()
        and not any(part in EXCLUDED_DIRECTORY_NAMES for part in candidate.parts)
    )


def scan_project(root_directory: Path) -> list[RuleViolation]:
    """Check every project file under the root and collect all violations.

    This is the function used by the command line, tests and continuous integration.
    """
    violations: list[RuleViolation] = []
    for file_path in iterate_project_files(root_directory):
        violations += check_single_file(file_path)
    return violations


def main(argument_list: list[str] | None = None) -> int:
    """Command line entry point that prints violations and returns an exit code.

    Returns 0 when the project is clean and 1 when any rule is broken.
    """
    parser = argparse.ArgumentParser(description="Check SitePay Agent project rules.")
    parser.add_argument("root", nargs="?", default=".", help="project root to scan")
    parsed_arguments = parser.parse_args(argument_list)
    root_directory = Path(parsed_arguments.root).resolve()
    violations = scan_project(root_directory)
    for violation in violations:
        print(violation.format_for_display())
    scanned_count = len(iterate_project_files(root_directory))
    print(f"Scanned {scanned_count} files, found {len(violations)} violations.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
