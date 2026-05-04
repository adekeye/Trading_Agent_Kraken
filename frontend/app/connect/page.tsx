"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import { KeyIcon, ShieldIcon, CheckIcon } from "../../components/Icons";

export default function ConnectPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    setLoading(true);
    try {
      const r = await api.post<{ connected: boolean; message: string }>("/kraken/connect", {
        api_key: apiKey,
        api_secret: apiSecret,
      });
      setMsg(r.message);
      setApiKey(""); setApiSecret("");
      setTimeout(() => router.push("/"), 800);
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 540, margin: "32px auto" }}>
      <h1 className="h1"><KeyIcon /> Connect Kraken <span className="h1-rule" /></h1>

      <div style={{
        display: "flex", gap: 8, padding: 10, marginBottom: 14,
        background: "var(--info-soft)", border: "1px solid var(--info)",
        borderRadius: "var(--radius-sm)", fontSize: 12, color: "var(--text-dim)",
      }}>
        <ShieldIcon className="icon lg" style={{ color: "var(--info)", flexShrink: 0 }} />
        <div>
          API key + secret are encrypted at rest with Fernet. Use a key with the
          minimum permissions: <span className="mono">Query Funds</span>,{" "}
          <span className="mono">Query/Modify/Cancel Orders</span>.
        </div>
      </div>

      <form onSubmit={submit}>
        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <div className="label" style={{ marginBottom: 4 }}>API Key</div>
            <input
              placeholder="paste API key"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              required
              autoComplete="off"
              spellCheck={false}
              style={{ fontFamily: "var(--font-mono)" }}
            />
          </div>
          <div>
            <div className="label" style={{ marginBottom: 4 }}>API Secret</div>
            <input
              placeholder="paste API secret"
              value={apiSecret}
              onChange={e => setApiSecret(e.target.value)}
              type="password"
              required
              autoComplete="off"
              style={{ fontFamily: "var(--font-mono)" }}
            />
          </div>
          <button className="primary" disabled={loading}>
            <CheckIcon /> {loading ? "Verifying…" : "Save credentials"}
          </button>
        </div>
      </form>
      {msg && <p className="ok-text" style={{ marginTop: 10, fontSize: 12 }}>{msg}</p>}
      {err && <p className="danger-text" style={{ marginTop: 10, fontSize: 12 }}>{err}</p>}
    </div>
  );
}
