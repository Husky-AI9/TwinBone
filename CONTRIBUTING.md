# Contributing to BoneTwin

Read `AGENTS.md` and the active phase in `CODEX_IMPLEMENTATION_SPEC.md` before making changes.
Keep work inside the current phase and preserve the medical safety boundary.

## Development

1. Install Python 3.12, uv, Node.js 22+, and pnpm 11.17.0.
2. Run `uv sync --locked` and `pnpm install --frozen-lockfile`.
3. Create a focused branch.
4. Make a small, test-backed change.
5. Run `make check`, or the equivalent commands documented in `README.md`.
6. Update `docs/implementation-status.md` when acceptance evidence changes.

Never commit real patient information, secrets, credentials, raw production logs, generated
presigned URLs, or unreviewed production document text. Fixtures must be plainly synthetic.

Pull requests should explain scope, safety impact, checks run, and any remaining risk.
