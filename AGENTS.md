# AGENTS.md

Notes for working on this repo in the Base44 sandbox. Manifests already describe the
project; this file only records what is not obvious.

## What this project is

`diydiag` is a **standard-library-only Python CLI**. There is no web server, no
database, and no third-party runtime dependency. Everything runs from
`python -m diydiag` inside one container.

## How the sandbox runs it

`docker-compose.base44.yml` starts one service, `diydiag`, whose base image is a plain
`python:3.12-slim` (no application source baked in) with the repo bind-mounted at
`/app`. Because the CLI has no HTTP surface, the preview is a real terminal session:
**ttyd** serves an interactive shell on host port 3000, so the actual CLI is driven
from the browser. Nothing about the app is stubbed.

Two gotchas worth knowing before editing the compose file:

- Debian no longer packages `ttyd`, so the Dockerfile pins the official static
  release binary (1.7.7) by SHA-256. Rebuild the image if you bump the version.
- ttyd parses **every** argument as its own option, so shell flags must come after a
  `--`. Without `--`, a trailing `-i` (or `--rcfile`) is consumed by ttyd and it
  segfaults the container. Keep the `--` before `bash --rcfile ... -i`.

The shell shown in the preview reads `.base44/bashrc` (banner + prompt). It is
sandbox-only scaffolding, not part of the app.

## Verifying it works

```bash
docker compose -f docker-compose.base44.yml up -d --build
docker compose -f docker-compose.base44.yml ps            # service must be (healthy)
docker compose -f docker-compose.base44.yml exec -T diydiag python -m pytest -q
docker compose -f docker-compose.base44.yml exec -T diydiag python eval/run_eval.py
docker compose -f docker-compose.base44.yml exec -T diydiag \
  python -m diydiag --intake examples/ram_shudder.json --html --json --out /tmp/ram
```

Expected: 7 tests pass; eval reports Top-1 1.00 / Top-3 1.00 over 14 cases; the
sample intake writes `/tmp/ram.md`, `/tmp/ram.html`, and `/tmp/ram.json` with the
torque-converter-clutch cause ranked first.

Write generated reports to `/tmp` (or a gitignored `report.*` name) so the repo stays
clean.

## External services

- **NHTSA vPIC (VIN decode) and NHTSA recalls**: free, no key, outbound HTTPS from
  the container works. Failures are caught in code and degrade gracefully
  (`--no-net` skips them entirely).
- **LLM pass** (`diydiag/llm.py`): opt-in via `DIYDIAG_API_KEY`. The app is fully
  functional without it - `refine()` returns the rule-engine result unchanged when the
  key is absent, so the key is **not** required to boot. It is declared as an optional
  Base44 secret and reaches the container through `env_file: /run/base44/app.env`,
  which is listed last so a dashboard value always wins. The provider base URL and
  model are non-secret config with working defaults in `llm.py`; to use a non-OpenAI
  provider, add `DIYDIAG_API_BASE` / `DIYDIAG_MODEL` to the service `environment:`.

## BASE44_PREVIEW_MODE

Passed through to the service as a bare variable. The app needs no sandbox-specific
overrides: ttyd does not validate `Host`/`Origin`, and the CLI has no URLs, cookies, or
CORS. With the flag unset, the compose file behaves identically - nothing is gated on
it here.
