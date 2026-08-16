.PHONY: install check format format-check lint typecheck test security-check dev \
	dev-infra dev-infra-down migrate seed test-integration test-e2e eval mcp-audit \
	deploy-demo

install:
	uv sync --locked
	pnpm install --frozen-lockfile

format:
	uv run ruff format .
	uv run ruff check --fix .
	pnpm format

format-check:
	uv run ruff format --check .
	pnpm format:check

lint:
	uv run ruff check .
	pnpm lint

typecheck:
	uv run mypy services evaluations scripts
	pnpm typecheck

test:
	uv run pytest -m "not integration"
	pnpm test

security-check:
	uv run python scripts/check_no_secrets.py

check: format-check lint typecheck test security-check

dev: dev-infra migrate seed
	npx pnpm dev

dev-infra:
	docker compose up -d --wait cockroach

dev-infra-down:
	docker compose down

migrate:
	uv run python -m scripts.migrate

seed:
	uv run python -m scripts.seed

test-integration:
	BONETWIN_RUN_DB_TESTS=1 uv run pytest -m integration

eval:
	uv run python -m evaluations.runners.memory_quality --check

mcp-audit:
	uv run python -m scripts.check_mcp_readonly
	uv run python -m scripts.run_cockroach_privilege_skill

test-e2e deploy-demo:
	@echo "$@ is intentionally deferred to a later implementation phase."
