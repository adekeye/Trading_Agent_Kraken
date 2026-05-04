"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "../../lib/api";
import { UserIcon } from "../../components/Icons";

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
    <div className="card" style={{ maxWidth: 380, margin: "48px auto" }}>
      <h1 className="h1"><UserIcon /> Create account <span className="h1-rule" /></h1>
      <form onSubmit={submit}>
        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <div className="label" style={{ marginBottom: 4 }}>Email</div>
            <input type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <div className="label" style={{ marginBottom: 4 }}>Password</div>
            <input
              type="password"
              placeholder="min 8 characters"
              value={password}
              onChange={e => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <button className="primary" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </div>
      </form>
      {err && <p className="danger-text" style={{ marginTop: 10, fontSize: 12 }}>{err}</p>}
      <p className="muted" style={{ marginTop: 14, fontSize: 12 }}>
        Already have an account? <Link href="/login" style={{ color: "var(--accent)" }}>Sign in</Link>
      </p>
    </div>
  );
}
