"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

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
    <div className="card" style={{ maxWidth: 560, margin: "32px auto" }}>
      <h1 className="h1">Connect Kraken</h1>
      <p className="muted">
        Your API key and secret are encrypted at rest with Fernet. Use a key that has{" "}
        <strong>only</strong> the permissions you need (Query Funds, Open/Close Orders).
      </p>
      <form onSubmit={submit}>
        <div style={{ display: "grid", gap: 12 }}>
          <input placeholder="API Key" value={apiKey} onChange={e => setApiKey(e.target.value)} required />
          <input
            placeholder="API Secret"
            value={apiSecret}
            onChange={e => setApiSecret(e.target.value)}
            type="password"
            required
          />
          <button className="primary" disabled={loading}>
            {loading ? "Verifying…" : "Save credentials"}
          </button>
        </div>
      </form>
      {msg && <p className="ok-text">{msg}</p>}
      {err && <p className="danger-text">{err}</p>}
    </div>
  );
}
