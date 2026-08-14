# mcp-app-demo

A minimal **MCP App** — an MCP server that serves an interactive UI widget which
renders directly inside the ChatGPT conversation, using the MCP Apps standard.

Sample project for:

- 🇻🇳 [Hướng dẫn thêm giao diện cho MCP server với OpenAI](https://camnangai.com/cong-cu/huong-dan-them-giao-dien-cho-mcp-server)
- 🇬🇧 [Add UI to Your MCP Server with OpenAI](https://camnangai.com/en/tools/add-ui-to-your-mcp-server)

## What it demonstrates

- A `ui://` **resource** serving a single-file HTML widget
  (`text/html;profile=mcp-app`)
- The **decoupled pattern** — a render tool that carries
  `_meta.ui.resourceUri`, and a plain data tool that does not
- The widget receiving data via `ontoolresult`, calling a server tool on its own
  with `callServerTool`, and pushing text back with `sendMessage`
- **Single-file bundling** with `vite-plugin-singlefile`, required because the
  host iframe blocks external scripts and styles

## Tools

| Tool | UI metadata | Purpose |
| --- | --- | --- |
| `show_metrics` | `_meta.ui.resourceUri` | Render tool — mounts the widget |
| `get_metrics` | none | Data tool — returns the same data as plain JSON |

## Run it

```bash
npm install
npm run dev        # builds the single-file UI, then starts the server
```

The server listens on `http://localhost:3001`, with the MCP endpoint at
`POST /mcp`. Opening `/mcp` in a browser returns "Cannot GET /mcp" — that is
expected, since the endpoint is POST only. Use `GET /` as the health check.

### Inspect it locally

```bash
npx @modelcontextprotocol/inspector
```

Point it at `http://localhost:3001/mcp` and check that `show_metrics` carries
`_meta.ui.resourceUri` while `get_metrics` does not.

### Connect it to ChatGPT

ChatGPT runs in the cloud and cannot reach `localhost`, so expose the server
with a tunnel:

```bash
npx -y cloudflared tunnel --url http://localhost:3001
```

If your network blocks outbound UDP, cloudflared will print a URL that never
connects — add `--protocol http2` to force it over TCP.

Then, with **Developer mode** enabled under *Settings → Security and login*,
add a new plugin pointing at `https://YOUR-TUNNEL-URL/mcp` with authentication
set to **No Auth**. Ask ChatGPT for the deployment metrics and the widget
renders in the conversation.

## Notes

The metrics are hardcoded in `buildMetrics()` — this is a demo of the UI
transport, not a real data source.

On page reload the host may replay a partial tool result, which can blank the
widget's chart until the tool runs again.
