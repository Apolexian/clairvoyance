SHELL := /bin/zsh
export PATH := $(HOME)/.local/bin:$(HOME)/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$(PATH)

.PHONY: fmt lint check install-hooks

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

# Install pre-commit hooks into .git/hooks
install-hooks:
	uv tool run pre-commit install

