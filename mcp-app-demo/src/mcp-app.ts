import { App } from "@modelcontextprotocol/ext-apps";

type Metric = { label: string; value: number; unit: string };
type Payload = { scope?: string; summary?: string; metrics?: Metric[] };

const app = new App({ name: "MCP App Demo", version: "1.0.0" });

const el = (id: string) => document.getElementById(id)!;
const setStatus = (s: string) => (el("status").textContent = s);

function render(data: Payload) {
  if (data.scope) el("scope").textContent = data.scope;
  if (data.summary) el("sub").textContent = data.summary;

  const metrics = data.metrics ?? [];
  const max = Math.max(...metrics.map((m) => m.value), 1);

  el("bars").innerHTML = metrics
    .map(
      (m) => `
      <div class="row">
        <span class="label">${m.label}</span>
        <div class="track"><div class="fill" style="width:${(m.value / max) * 100}%"></div></div>
        <span class="val">${m.value}${m.unit}</span>
      </div>`,
    )
    .join("");
}

// Data pushed down by the host when the tool runs (ui/notifications/tool-result)
app.ontoolresult = (result) => {
  const data = result.structuredContent as Payload | undefined;
  if (data) {
    render(data);
    setStatus("updated from tool result");
  }
};

// The UI calling a server tool on its own, independent of the model
async function refresh() {
  const btn = el("refresh") as HTMLButtonElement;
  btn.disabled = true;
  setStatus("calling server tool…");
  try {
    const res = await app.callServerTool({
      name: "get_metrics",
      arguments: { scope: "last 7 days" },
    });
    const data = (res as { structuredContent?: Payload }).structuredContent;
    if (data) render(data);
    setStatus("refreshed via tools/call");
  } catch (err) {
    setStatus(`error: ${String(err)}`);
  } finally {
    btn.disabled = false;
  }
}

// Push a line of context back into the conversation
async function sendToChat() {
  setStatus("sending to chat…");
  try {
    await app.sendMessage({ message: "Summarise the deployment metrics shown above." });
    setStatus("sent to chat");
  } catch (err) {
    setStatus(`error: ${String(err)}`);
  }
}

el("refresh").addEventListener("click", refresh);
el("detail").addEventListener("click", sendToChat);

// Render placeholder data so the widget looks right even before the host connects
render({
  scope: "last 7 days",
  summary: "Deployment throughput and reliability across the main service.",
  metrics: [
    { label: "Deploys", value: 48, unit: "" },
    { label: "Success", value: 96, unit: "%" },
    { label: "Lead time", value: 22, unit: "m" },
    { label: "Rollbacks", value: 2, unit: "" },
  ],
});

app.connect().then(
  () => setStatus("connected to host"),
  () => setStatus("standalone preview"),
);
