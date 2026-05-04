"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const r = await api.post<{ access_token: string }>("/auth/register", { email, password });
      setToken(r.access_token);
      router.push("/connect");
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "32px auto" }}>
      <h1 className="h1">Create account</h1>
      <form onSubmit={submit}>
        <div style={{ display: "grid", gap: 12 }}>
          <input type="email" placeholder="email" value={email} onChange={e => setEmail(e.target.value)} required />
          <input
            type="password"
            placeholder="password (min 8 chars)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            minLength={8}
            required
          />
          <button className="primary" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </div>
      </form>
      {err && <p className="danger-text">{err}</p>}
      <p className="muted" style={{ marginTop: 12 }}>
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </div>
  );
}
