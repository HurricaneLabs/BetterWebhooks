## Overview

BetterWebhooks is built in part using the Splunk UI toolkit. The instructions below for building come from that portion of the app.

For app docs, go [here](https://betterwebhooks.readthedocs.io/).

## Getting Started

1. Clone the repo.
2. Install yarn (>= 1.2) if you haven't already: `npm install --global yarn`.
3. Run the setup task: `yarn run setup`.

After this step, the following tasks will be available:

-   `start` – Run the `start` task for each project
-   `build` – Create a production bundle for all projects
-   `test` – Run unit tests for each project
-   `lint` – Run JS and CSS linters for each project
-   `format` – Run prettier to auto-format `*.js`, `*.jsx` and `*.css` files. This command will overwrite files without
    asking, `format:verify` won't.

Running `yarn run setup` once is required to enable all other tasks. The command might take a few minutes to finish.

## Building the SPL

To produce a distributable `BetterWebhooks.spl` file:

```bash
yarn run package
```

This runs the full build and packages the output into a `.spl` archive in the project root. This is the file you install
into Splunk or submit to Splunkbase.

## Linting and Validation

### Python (ruff)

```bash
pip install ruff
ruff check packages/better-webhooks/src/main/resources/splunk/bin/
```

### Splunk AppInspect

AppInspect validates the app against the same checks Splunk runs during Splunkbase submission. Build the SPL first, then inspect it:

```bash
yarn run package
pip install splunk-appinspect
splunk-appinspect inspect BetterWebhooks.spl --mode precert
```

Both checks also run automatically in CI on every push and pull request.
