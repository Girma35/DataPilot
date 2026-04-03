"use client";

import { useCallback, useState } from "react";

type StepState = "idle" | "loading" | "done" | "error";

function StepBadge({ n, label, active }: { n: number; label: string; active: boolean }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${
        active
          ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-black"
          : "border-zinc-200 text-zinc-600 dark:border-zinc-700 dark:text-zinc-400"
      }`}
    >
      <span className="font-mono text-xs opacity-80">{n}</span>
      {label}
    </div>
  );
}

export function UserWorkflowPanel() {
  const [healthState, setHealthState] = useState<StepState>("idle");
  const [healthBody, setHealthBody] = useState<string>("");

  const [sql, setSql] = useState("SELECT 1 AS ok");
  const [limit, setLimit] = useState("50");
  const [queryState, setQueryState] = useState<StepState>("idle");
  const [queryBody, setQueryBody] = useState<string>("");

  const [alertMessage, setAlertMessage] = useState("DataPilot workflow test");
  const [alertChannel, setAlertChannel] = useState<"slack" | "discord" | "both">("both");
  const [alertState, setAlertState] = useState<StepState>("idle");
  const [alertBody, setAlertBody] = useState<string>("");

  const [vaultMessage, setVaultMessage] = useState("DataPilot intermediary agent (Token Vault → Slack)");
  const [slackChannelId, setSlackChannelId] = useState("");
  const [vaultState, setVaultState] = useState<StepState>("idle");
  const [vaultBody, setVaultBody] = useState<string>("");

  const runHealth = useCallback(async () => {
    setHealthState("loading");
    setHealthBody("");
    try {
      const res = await fetch("/api/datapilot/health");
      const data = await res.json().catch(() => ({}));
      setHealthBody(JSON.stringify(data, null, 2));
      setHealthState(res.ok ? "done" : "error");
    } catch (e) {
      setHealthBody(String(e));
      setHealthState("error");
    }
  }, []);

  const runQuery = useCallback(async () => {
    setQueryState("loading");
    setQueryBody("");
    const lim = limit.trim() ? parseInt(limit, 10) : undefined;
    try {
      const res = await fetch("/api/datapilot/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sql,
          limit: Number.isFinite(lim) ? lim : undefined,
        }),
      });
      const data = await res.json().catch(() => ({}));
      setQueryBody(JSON.stringify(data, null, 2));
      setQueryState(res.ok ? "done" : "error");
    } catch (e) {
      setQueryBody(String(e));
      setQueryState("error");
    }
  }, [sql, limit]);

  const runAlert = useCallback(async () => {
    setAlertState("loading");
    setAlertBody("");
    try {
      const res = await fetch("/api/datapilot/alert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: alertMessage, channel: alertChannel }),
      });
      const data = await res.json().catch(() => ({}));
      setAlertBody(JSON.stringify(data, null, 2));
      setAlertState(res.ok ? "done" : "error");
    } catch (e) {
      setAlertBody(String(e));
      setAlertState("error");
    }
  }, [alertMessage, alertChannel]);

  const runVaultSlack = useCallback(async () => {
    setVaultState("loading");
    setVaultBody("");
    try {
      const res = await fetch("/api/datapilot/agent/slack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: vaultMessage,
          slack_channel: slackChannelId.trim(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      setVaultBody(JSON.stringify(data, null, 2));
      setVaultState(res.ok ? "done" : "error");
    } catch (e) {
      setVaultBody(String(e));
      setVaultState("error");
    }
  }, [vaultMessage, slackChannelId]);

  return (
    <section className="mt-10 w-full space-y-10 border-t border-zinc-200 pt-10 dark:border-zinc-800">
      <div className="flex flex-wrap gap-2">
        <StepBadge n={1} label="API health" active />
        <StepBadge n={2} label="Read-only SQL" active={healthState === "done"} />
        <StepBadge n={3} label="Webhooks" active={queryState === "done"} />
        <StepBadge n={4} label="Token Vault agent" active={alertState === "done"} />
      </div>

      <div className="space-y-4 rounded-2xl border border-zinc-200 bg-zinc-50/80 p-6 dark:border-zinc-800 dark:bg-zinc-950/50">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">1. Backend health</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Calls your FastAPI service with your session token (<code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">DATAPILOT_API_URL</code>, default{" "}
          <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">http://127.0.0.1:8000</code>).
        </p>
        <button
          type="button"
          onClick={runHealth}
          disabled={healthState === "loading"}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200"
        >
          {healthState === "loading" ? "Checking…" : "Run health check"}
        </button>
        {healthBody ? (
          <pre className="max-h-48 overflow-auto rounded-lg border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-700 dark:bg-black">
            {healthBody}
          </pre>
        ) : null}
      </div>

      <div className="space-y-4 rounded-2xl border border-zinc-200 bg-zinc-50/80 p-6 dark:border-zinc-800 dark:bg-zinc-950/50">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">2. Read-only query</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Executes via <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">POST /query</code>. Requires a valid database URL on the API server.
        </p>
        <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500">SQL</label>
        <textarea
          value={sql}
          onChange={(e) => setSql(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-zinc-300 bg-white p-3 font-mono text-sm dark:border-zinc-600 dark:bg-black"
          spellCheck={false}
        />
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-500">Row limit</label>
            <input
              type="number"
              min={1}
              max={10000}
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className="w-28 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-black"
            />
          </div>
          <button
            type="button"
            onClick={runQuery}
            disabled={queryState === "loading"}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200"
          >
            {queryState === "loading" ? "Running…" : "Run query"}
          </button>
        </div>
        {queryBody ? (
          <pre className="max-h-64 overflow-auto rounded-lg border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-700 dark:bg-black">
            {queryBody}
          </pre>
        ) : null}
      </div>

      <div className="space-y-4 rounded-2xl border border-zinc-200 bg-zinc-50/80 p-6 dark:border-zinc-800 dark:bg-zinc-950/50">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">3. Slack / Discord (webhooks)</h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Calls <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">POST /alert</code>. Webhooks must be set in the API environment.
        </p>
        <input
          type="text"
          value={alertMessage}
          onChange={(e) => setAlertMessage(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-black"
          placeholder="Message"
        />
        <select
          value={alertChannel}
          onChange={(e) => setAlertChannel(e.target.value as typeof alertChannel)}
          className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-black"
        >
          <option value="slack">Slack</option>
          <option value="discord">Discord</option>
          <option value="both">Both</option>
        </select>
        <button
          type="button"
          onClick={runAlert}
          disabled={alertState === "loading"}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200"
        >
          {alertState === "loading" ? "Sending…" : "Send alert"}
        </button>
        {alertBody ? (
          <pre className="max-h-48 overflow-auto rounded-lg border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-700 dark:bg-black">
            {alertBody}
          </pre>
        ) : null}
      </div>

      <div className="space-y-4 rounded-2xl border border-violet-200 bg-violet-50/60 p-6 dark:border-violet-900 dark:bg-violet-950/30">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          4. Intermediary agent — Auth0 Token Vault → Slack
        </h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Calls <code className="rounded bg-violet-200/80 px-1 dark:bg-violet-900">POST /agent/slack</code>. The API exchanges your Auth0 access token for a{" "}
          <strong className="font-medium text-zinc-800 dark:text-zinc-200">Slack token from Token Vault</strong>, then posts as{" "}
          <em>you</em> (no shared bot webhook). Requires Slack connected via Auth0 Connected Accounts + Token Vault, Custom API client credentials on the
          server, and your SPA audience set to your <strong className="font-medium">DataPilot API</strong> identifier.
        </p>
        <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500">Slack channel ID</label>
        <input
          type="text"
          value={slackChannelId}
          onChange={(e) => setSlackChannelId(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-sm dark:border-zinc-600 dark:bg-black"
          placeholder="C01234567890"
        />
        <input
          type="text"
          value={vaultMessage}
          onChange={(e) => setVaultMessage(e.target.value)}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-black"
          placeholder="Message"
        />
        <button
          type="button"
          onClick={runVaultSlack}
          disabled={vaultState === "loading" || !slackChannelId.trim()}
          className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50 dark:bg-violet-600 dark:hover:bg-violet-500"
        >
          {vaultState === "loading" ? "Exchanging & posting…" : "Post via Token Vault"}
        </button>
        {vaultBody ? (
          <pre className="max-h-64 overflow-auto rounded-lg border border-zinc-200 bg-white p-3 text-xs dark:border-zinc-700 dark:bg-black">
            {vaultBody}
          </pre>
        ) : null}
      </div>
    </section>
  );
}
