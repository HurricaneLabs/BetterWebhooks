# CLAUDE.md

BetterWebhooks is a Splunk app providing an enhanced webhook alert action (adapted from Splunk's stock `alert_webhook`) with HMAC signing, OAuth, proxy support, and a credential-management UI built on the Splunk UI toolkit. Docs: https://betterwebhooks.readthedocs.io/

## Commands (yarn + lerna monorepo; no Makefile exists)

- `yarn run setup` — install deps and build all packages (required once before anything else)
- `yarn run build` — build all packages (`lerna run build`)
- `yarn run start` — webpack watch mode for each package
- `yarn run test` — run unit tests (jest; only `packages/webhook-credentials` has tests)
- `yarn run lint` — eslint + stylelint per package; `yarn run format` / `format:verify` — prettier
- `yarn run package` — full build, then bundle `BetterWebhooks.spl` into the repo root (via `package.js`)
- `ruff check packages/better-webhooks/src/main/resources/splunk/bin/` — Python lint (config in `ruff.toml`)
- `splunk-appinspect inspect BetterWebhooks.spl --mode precert` — Splunkbase validation (build the SPL first)

CI (`.github/workflows/`): `ci.yml` runs ruff + AppInspect on every push/PR; `build-spl.yml` builds the `.spl` artifact and attaches it to releases.

## Architecture

- Lerna / Yarn-workspaces monorepo with two packages; Node >= 14, React 16, `@splunk/react-ui` 4.x on `main`. NOTE: remote branch `wip/react-ui-5-migration` (unmerged, newer than `main`) is migrating the UI stack.
- `packages/better-webhooks` is the Splunk app itself: the app payload lives under `src/main/resources/splunk/` (Python alert action in `bin/`, `.conf` files in `default/`, vendored `loguru` in `lib/`), and a React credentials page under `src/main/webapp/pages/credentials/` is webpack-built into it.
- `packages/webhook-credentials` is a reusable React component library (`WebhookCredentials.jsx` + modals) consumed by the app's credentials page; it holds the jest tests.
- Backend flow: `bin/better_webhook.py` runs as the alert action, pulls JSON-encoded credentials from Splunk `storage/passwords` (realm `better_webhooks:<name>:`), builds auth headers via `hmac_helper.py` / `oauth_helper.py`, and POSTs the payload with `requests` (optional proxy).
- Packaging flow: `package.js` runs setup + the app package's `bin/build.js`, stages output in `packages/better-webhooks/stage/`, and tars it into `BetterWebhooks.spl`.
- `docs/` is a separate Sphinx project published to Read the Docs (`.readthedocs.yaml`); its `docs/Makefile` is Sphinx boilerplate, not the app build.

## Repo Map

```
package.json / lerna.json     # workspace root; all dev tasks are yarn scripts here
package.js                    # SPL packaging script (yarn run package)
ruff.toml / babel.config.js / .prettierrc   # shared toolchain config
.github/workflows/            # ci.yml (ruff + AppInspect), build-spl.yml (SPL artifact + release upload)
docs/
  source/                     # Sphinx docs (installation, alert action, credentials, proxy, troubleshooting)
packages/
  better-webhooks/            # the Splunk app package
    bin/build.js              # assembles splunk resources + webpack output into stage/
    src/main/resources/splunk/
      bin/better_webhook.py   # alert action entry point (+ hmac_helper.py, oauth_helper.py)
      default/                # alert_actions.conf, app.conf, better_webhooks.conf, UI XML
      lib/                    # vendored loguru 0.7.2
    src/main/webapp/pages/credentials/index.jsx   # React page entry
  webhook-credentials/        # reusable credential-management React components
    src/WebhookCredentials.jsx  # main component (modals, forms, http_utils.js)
```
