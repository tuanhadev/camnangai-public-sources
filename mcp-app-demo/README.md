# mcp-app-demo

A minimal **MCP App** — an MCP server that serves an interactive UI widget which
renders directly inside the ChatGPT conversation, using the MCP Apps standard.

This is the finished project for:

- 🇻🇳 [Hướng dẫn thêm giao diện cho MCP server với OpenAI](https://camnangai.com/cong-cu/huong-dan-them-giao-dien-cho-mcp-server)
- 🇬🇧 [Add UI to Your MCP Server with OpenAI](https://camnangai.com/en/tools/add-ui-to-your-mcp-server)

## Project structure

```text
mcp-app-demo/
├── package.json
├── tsconfig.json
├── vite.config.ts      # bundles the UI into a single HTML file
├── server.ts           # MCP server, reads ./dist/mcp-app.html
├── mcp-app.html        # UI entry point
└── src/
    └── mcp-app.ts      # client-side UI logic
```

## Which file each step of the guide produces

| Guide step                     | File                          | What it adds                                              |
| ------------------------------ | ----------------------------- | --------------------------------------------------------- |
| Step 1 — create the project     | `package.json`, `tsconfig.json` | Dependencies and the `build` / `serve` / `dev` scripts    |
| Step 2 — build the UI           | `src/mcp-app.ts`, `mcp-app.html` | The `App` class, `ontoolresult`, `callServerTool`      |
| Step 3 — bundle to one file     | `vite.config.ts`              | `vite-plugin-singlefile` and the `INPUT` entry point       |
| Step 4 — register the resource  | `server.ts`                   | The `ui://` resource and the `render_view` tool            |
| Step 5 — run and inspect        | —                             | `npm run dev`, then MCP Inspector                          |
| Step 6 — connect to ChatGPT     | —                             | cloudflared tunnel, then add the plugin                    |

The names match the guide: the UI resource is `ui://mcp-app/main.html`, the render
tool is `render_view`, and the server is registered as `UI Server`.

## What this sample adds beyond the guide

The guide teaches in fragments — it writes `renderUI(data)` and `/* schema */` and
moves on. A runnable project needs more, so this sample also contains:

- **`get_metrics`** — a second, plain data tool with **no** UI metadata. This is the
  other half of the decoupled pattern the guide describes: the render tool mounts the
  widget, the data tool returns the same data as plain JSON.
- **`buildMetrics()`** — hardcoded sample data standing in for a real data source.
- **The actual widget rendering** in `src/mcp-app.ts` — the bar chart, the refresh
  button, and the "send to chat" action. The guide only shows the wiring around it.

## Run it

```bash
npm install
npm run dev        # builds the single-file UI, then starts the server
```

Use `npm run dev`, not `npm run serve` — `server.ts` reads `dist/mcp-app.html` at
startup, so the UI has to be built first.

The server listens on `http://localhost:3001`, with the MCP endpoint at `POST /mcp`.
Opening `/mcp` in a browser returns "Cannot GET /mcp" — that is expected, since the
endpoint is POST only. Use `GET /` as the health check.

### Inspect it locally

```bash
npx @modelcontextprotocol/inspector
```

Point it at `http://localhost:3001/mcp` and check that `render_view` carries
`_meta.ui.resourceUri` while `get_metrics` does not.

### Connect it to ChatGPT

ChatGPT runs in the cloud and cannot reach `localhost`, so expose the server with a
tunnel:

```bash
npx -y cloudflared tunnel --url http://localhost:3001
```

If your network blocks outbound UDP, cloudflared will print a URL that never
connects — add `--protocol http2` to force it over TCP.

Then, with **Developer mode** enabled under _Settings → Security and login_, open
**Plugins**, choose **New Plugin**, and point it at `https://YOUR-TUNNEL-URL/mcp`
with authentication set to **No Auth**. Ask ChatGPT for the deployment metrics and
the widget renders in the conversation.

## Notes

The metrics are hardcoded in `buildMetrics()` — this is a demo of the UI transport,
not a real data source.

On page reload the host may replay a partial tool result, which can blank the
widget's chart until the tool runs again.
