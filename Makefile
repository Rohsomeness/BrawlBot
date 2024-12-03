.PHONY: test lint run

test:
    pytest

lint:
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

run:
	python3 main.py
