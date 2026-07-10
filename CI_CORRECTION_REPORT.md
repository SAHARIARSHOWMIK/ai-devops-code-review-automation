# CI correction report

## Failure addressed

The frontend job failed during `npm run lint` with:

```text
TS2688: Cannot find type definition file for 'vite/client'.
```

The dependency lock referenced a private build-environment registry and the workflow did not explicitly force installation of development dependencies. This made the Vite type package unreliable on a clean GitHub runner.

## Corrections

- Regenerated the frontend dependency lock and replaced private-registry artifact URLs with the public npm registry.
- Added a repository-level frontend `.npmrc` using `https://registry.npmjs.org/`.
- Explicitly installs development dependencies with `npm ci --include=dev` in CI and Docker.
- Added a CI guard that verifies `node_modules/vite/client.d.ts` exists before TypeScript runs.
- Updated the frontend toolchain to Node.js 22, Vite 8.1.4, React plugin 6.0.3, TypeScript 5.8.3, and React Router 6.30.4.
- Removed the known frontend dependency advisories; `npm audit` reports zero vulnerabilities.
- Added CI timeouts, concurrency cancellation, read-only permissions, named steps, backend formatting/lint/type/security checks, and analyzer-worker image build coverage.
- Added Ruff, mypy, and Bandit development dependencies and corrected the findings they exposed.
- Added safe shared pooling for in-memory SQLite and a regression test.
- Replaced swallowed background/context exceptions with logged fallbacks.
- Hardened Windows setup/test scripts and the analyzer-worker Docker toolchain.

## Verification completed

- Backend Ruff formatting: passed.
- Backend Ruff lint: passed.
- Backend mypy type check: passed.
- Backend Bandit medium/high scan: passed.
- Backend compilation: passed.
- Backend tests: 53 passed, 82% measured coverage.
- Python dependency consistency (`pip check`): passed.
- Alembic migration to head: passed.
- FastAPI startup, demo seed, login, organization, and repository smoke tests: passed.
- Clean frontend dependency installation: passed.
- Vite client type definition check: passed.
- TypeScript check: passed.
- Production frontend build: passed.
- Frontend preview smoke test: passed.
- npm audit: zero vulnerabilities.
- Workflow YAML, Docker Compose YAML, Docker build paths, lockfile JSON, and public-registry references: validated.

Docker is unavailable in the artifact sandbox, so the three image builds were not executed locally. The corrected GitHub Actions workflow builds the backend, frontend, and analyzer-worker images after the test jobs pass.

## Analyzer image follow-up correction (2026-07-11)

A later analyzer-worker build exposed an additional Composer platform requirement. Laravel Pint 1.24 requires PHP's `ext-xml` in addition to `ext-mbstring` and `ext-tokenizer`. The analyzer image now installs and validates the complete PHP runtime needed by the global Composer tools:

- `php-curl`
- `php-mbstring`
- `php-xml`
- `php-zip`
- `unzip`

Composer now uses a deterministic global home (`/opt/composer`), root-container mode is explicit, and Python, npm, and Composer installations are split into separate Docker layers. The Dockerfile verifies required PHP extensions and executes `phpstan --version` and `pint --version` during the image build. CI also smoke-tests the complete analyzer toolchain after the image is built.
