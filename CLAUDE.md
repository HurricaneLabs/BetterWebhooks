# CLAUDE.md

BetterWebhooks is a Splunk app providing an enhanced webhook alert action (adapted from Splunk's stock `alert_webhook`) with HMAC signing, OAuth, proxy support, and a credential-management UI built on the Splunk UI toolkit. Docs: https://betterwebhooks.readthedocs.io/

## Commands (yarn + lerna monorepo; no Makefile exists)

- `yarn run setup` — install deps and build all packages (required once before anything else)
- `yarn run build` — build all packages (`lerna run build`)
- `yarn run start` — webpack watch mode for each package
- `yarn run test` — run JS unit tests (jest; only `packages/webhook-credentials` has them)
- `yarn run lint` — eslint + stylelint per package; `yarn run format` / `format:verify` — prettier
- `yarn run package` — full build, then bundle `BetterWebhooks.spl` into the repo root (via `package.js`)
- `ruff check packages/better-webhooks/src/main/resources/splunk/bin/ packages/better-webhooks/tests/` — Python lint (config in `ruff.toml`)
- `uv run pytest` — Python unit tests for the alert action (`packages/better-webhooks/tests/`; config and dev deps in the root `pyproject.toml`)
- `splunk-appinspect inspect BetterWebhooks.spl --mode precert` — Splunkbase validation (build the SPL first)

CI (`.github/workflows/`): `ci.yml` runs ruff, pytest on Python 3.9 and 3.13 (the app requires Splunk 10.4+, which runs the alert action on 3.13; the 3.9 job dates from the old 10.0 floor; locally `uv run --python 3.9 pytest`), the JS unit tests, JS lint (`yarn run lint`, failing on any warning) + prettier check (`format:verify`) and AppInspect on every push/PR; `build-spl.yml` builds the `.spl` artifact and attaches it to releases.

## Architecture

- Lerna / Yarn-workspaces monorepo with two packages; Node 18 (pinned in `.node-version`), React 16, `@splunk/react-ui` 5.11, `@splunk/themes` 1.8.
- `packages/better-webhooks` is the Splunk app itself: the app payload lives under `src/main/resources/splunk/` (Python alert action in `bin/`, `.conf` files in `default/`, vendored `loguru` in `lib/`), and a React credentials page under `src/main/webapp/pages/credentials/` is webpack-built into it. The view (`default/data/ui/views/credentials.xml`) uses Splunk's built-in `pages/splunk_ui_app.html` template (10.4+), which loads `appserver/static/pages/<view name>.js`, so the page directory and the view must share a name. The app ships no Mako template.
- `packages/webhook-credentials` is a reusable React component library (`WebhookCredentials.jsx` + modals) consumed by the app's credentials page; it holds the jest tests.
- Backend flow: `bin/better_webhook.py` runs as the alert action, pulls JSON-encoded credentials from Splunk `storage/passwords` (realm `better_webhooks:<name>:`), builds auth headers via `hmac_helper.py` / `oauth_helper.py`, and POSTs the payload with `requests` (optional proxy). `log_redaction.py` scrubs the credential's secret fields (`SECRET_FIELDS`), the OAuth token, and the path, query and userinfo of the webhook and token URLs from every log line; request and response bodies are never logged, and URLs only by host. Every webhook, token and proxy URL goes through `log_redaction.url_parses()` before anything logs or sends it: a raw `#`, `/`, `?` or `\` in a password would otherwise get the password's start logged as the host.
- Packaging flow: `package.js` runs setup + the app package's `bin/build.js`, stages output in `packages/better-webhooks/stage/`, and tars it into `BetterWebhooks.spl`.
- `docs/` is a separate Sphinx project published to Read the Docs (`.readthedocs.yaml`); its `docs/Makefile` is Sphinx boilerplate, not the app build.

## Repo Map

```
package.json / lerna.json     # workspace root; all dev tasks are yarn scripts here
package.js                    # SPL packaging script (yarn run package)
ruff.toml / babel.config.js / .prettierrc   # shared toolchain config
pyproject.toml / uv.lock      # Python test tooling only (pytest, responses); the app installs nothing
.github/workflows/            # ci.yml (ruff, pytest, JS tests, JS lint/format, AppInspect), build-spl.yml (SPL artifact + release upload)
docs/
  source/                     # Sphinx docs (installation, alert action, credentials, proxy, troubleshooting)
packages/
  better-webhooks/            # the Splunk app package
    bin/build.js              # assembles splunk resources + webpack output into stage/
    src/main/resources/splunk/
      bin/better_webhook.py   # alert action entry point (+ hmac_helper.py, oauth_helper.py, log_redaction.py)
      default/                # alert_actions.conf, app.conf, better_webhooks.conf, UI XML
      lib/                    # vendored loguru 0.7.2
    src/main/webapp/pages/credentials/index.jsx   # React page entry
    tests/                    # pytest for the alert action; outside resources/splunk so it never ships
  webhook-credentials/        # reusable credential-management React components
    src/WebhookCredentials.jsx  # main component (modals, forms, http_utils.js)
```
