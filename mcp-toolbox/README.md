# MCP Toolbox — read-only BigQuery tools

This directory holds `tools.yaml`: parameterized, **read-only** BigQuery tools exposed to the
FinSight agents via the [MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox)
(the project was renamed from `genai-toolbox` to `mcp-toolbox`; the binary is still called
`toolbox`).

> The toolbox binary itself is **not** checked into this repo (`.gitignore`d) and can't be
> downloaded by an agent — no outbound binary fetch available in this environment. This is a
> 🧑 **human step**.

## 1. Download the binary (macOS, Apple Silicon / arm64)

```bash
cd mcp-toolbox
export VERSION=1.6.0   # check https://github.com/googleapis/mcp-toolbox/releases for newer
curl -L -o toolbox "https://storage.googleapis.com/mcp-toolbox-for-databases/v${VERSION}/darwin/arm64/toolbox"
chmod +x toolbox
```

Alternative (Homebrew):

```bash
brew install mcp-toolbox
```

If you use Homebrew, replace `./toolbox` with `toolbox` (or `mcp-toolbox`, check
`brew info mcp-toolbox` for the installed command name) in the commands below.

## 2. Run it

From the `mcp-toolbox/` directory (so relative source config resolves, and so env var
interpolation in `tools.yaml` picks up `.env`):

```bash
cd mcp-toolbox
export $(grep -v '^#' ../.env | xargs)   # load BIGQUERY_PROJECT etc. into the shell
./toolbox --config "tools.yaml"
```

This starts an MCP server on **`http://127.0.0.1:5000`** by default (matches `TOOLBOX_URL` in
`.env`). Run it in its own terminal — it needs to stay running while you use the agents.

To eyeball the loaded tools visually instead of reading logs, add `--ui` and open the printed
local URL in a browser.

Toolbox authenticates to BigQuery via your gcloud **Application Default Credentials** (ADC) —
the same `gcloud auth application-default login` already set up for this project. No service
account key needed.

## 3. Verify

- Check the terminal output for a message confirming the tools loaded (or use `--ui`).
- Or query the MCP endpoint directly, e.g. with
  [MCP Inspector](https://github.com/modelcontextprotocol/inspector):
  `npx @modelcontextprotocol/inspector`, then connect to `http://127.0.0.1:5000/mcp`.
- You should see the `finops_readonly` toolset with 4 tools: `get_daily_sales`,
  `get_revenue_by_period`, `get_orders_by_category`, `compare_period_over_period`.

## Why this is read-only

Every tool in `tools.yaml` is a `bigquery-sql` tool with a **fixed** `SELECT` statement and typed
named parameters (`@start_date`, etc.) — there is no `bigquery-execute-sql` tool exposed, so an
agent can never submit arbitrary SQL, only fill in the parameters of these four pre-written
queries. See the comment block at the top of `tools.yaml` for more detail, including why
`writeMode: blocked` alone isn't sufficient (it only restricts `bigquery-execute-sql`, which we
don't expose anyway).
