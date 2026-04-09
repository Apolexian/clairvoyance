SHELL := /bin/zsh
export PATH := $(HOME)/.local/bin:$(HOME)/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$(PATH)

.PHONY: fmt lint check clean nuke analyse dump install-hooks

# Format everything
fmt:
	uv tool run ruff format .
	uv tool run ruff check --fix .
	@command -v npx >/dev/null 2>&1 && npx -y prettier --write "js/**/*.js" || echo "npx not found, skipping JS formatting"

# Lint without fixing
lint:
	uv tool run ruff check .

# Check formatting without changing files (CI-friendly)
check:
	uv tool run ruff format --check .
	uv tool run ruff check .
	@command -v npx >/dev/null 2>&1 && npx -y prettier --check "js/**/*.js" || echo "npx not found, skipping JS check"

# Remove logs, sessions, pycache (keeps discovery/)
clean:
	rm -f *.log
	rm -rf sessions/
	rm -rf __pycache__/ lib/__pycache__/

# Remove EVERYTHING including discovery (full reset)
nuke: clean
	rm -rf discovery/

# Analyse discovery class dump → discovery/analysis.md + discovery/interesting.json
analyse:
	@test -f discovery/class_dump.json || (echo "No class_dump.json found. Run discover.py first." && exit 1)
	python3 analyse.py

# Run the data-driven dump collector (requires interesting.json)
dump:
	@test -f discovery/interesting.json || (echo "No interesting.json found. Run: make analyse" && exit 1)
	uv run collect.py --modules dump --label dump

# Install pre-commit hooks into .git/hooks
install-hooks:
	uv tool run pre-commit install

