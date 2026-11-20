.PHONY: test check-rules check

test:
	python -m pytest tests

check-rules:
	python scripts/check_project_rules.py .

check: check-rules test
