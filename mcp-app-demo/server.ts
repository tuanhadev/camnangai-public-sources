import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import express from "express";
import cors from "cors";
import fs from "node:fs/promises";
import { z } from "zod";

const UI_URI = "ui://mcp-app/main.html";
const PORT = Number(process.env.PORT ?? 3001);

function buildMetrics(scope: string) {
  return {
    scope,
    summary: "Deployment throughput and reliability across the main service.",
    metrics: [
      { label: "Deploys", value: 48, unit: "" },
      { label: "Success", value: 96, unit: "%" },
      { label: "Lead time", value: 22, unit: "m" },
      { label: "Rollbacks", value: 2, unit: "" },
    ],
  };
}

function createServer() {
  const server = new McpServer({ name: "UI Server", version: "1.0.0" });

  // Serve the bundled single-file HTML as a ui:// resource
  registerAppResource(server, "McpAppUI", UI_URI, { mimeType: RESOURCE_MIME_TYPE }, async () => {
    const html = await fs.readFile(new URL("./dist/mcp-app.html", import.meta.url), "utf-8");
    return { contents: [{ uri: UI_URI, mimeType: RESOURCE_MIME_TYPE, text: html }] };
  });

  // Render tool — carries the UI metadata that mounts the resource
  registerAppTool(
    server,
    "render_view",
    {
      title: "Show deployment metrics",
      description: "Display an interactive deployment metrics dashboard.",
      inputSchema: { scope: z.string().optional().describe("Time window, e.g. 'last 7 days'") },
      _meta: { ui: { resourceUri: UI_URI } },
    },
    async ({ scope }) => {
      const data = buildMetrics(scope ?? "last 7 days");
      return {
        content: [{ type: "text", text: `Showing deployment metrics for ${data.scope}.` }],
        structuredContent: data,
      };
    },
  );

  // Data tool — plain data, no UI metadata (the decoupled pattern)
  server.registerTool(
    "get_metrics",
    {
      title: "Get deployment metrics",
      description: "Return raw deployment metrics as data.",
      inputSchema: { scope: z.string().optional() },
    },
    async ({ scope }) => {
      const data = buildMetrics(scope ?? "last 7 days");
      return {
        content: [{ type: "text", text: JSON.stringify(data) }],
        structuredContent: data,
      };
    },
  );

  return server;
}

const app = express();
app.use(cors({ exposedHeaders: ["Mcp-Session-Id"] }));
app.use(express.json());

app.get("/", (_req, res) => {
  res.type("text/plain").send("MCP App Demo — POST /mcp for the MCP endpoint.");
});

app.post("/mcp", async (req, res) => {
  try {
    const server = createServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });
    res.on("close", () => {
      transport.close();
      server.close();
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error("MCP request failed:", err);
    if (!res.headersSent) res.status(500).json({ error: String(err) });
  }
});

app.listen(PORT, () => {
  console.log(`MCP App Demo listening on http://localhost:${PORT}/mcp`);
});
