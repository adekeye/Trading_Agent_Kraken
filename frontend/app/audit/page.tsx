"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { AuditLog } from "../../lib/types";

export default function AuditPage() {
  const router = useRouter();
  const [items, setItems] = useState<AuditLog[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.get<AuditLog[]>("/audit-logs")
      .then(setItems)
      .catch(e => setErr((e as Error).message));
  }, [router]);

  return (
    <div>
      <h1 className="h1">Audit Log</h1>
      <div className="card">
        {err && <p className="danger-text">{err}</p>}
        {!items && !err && <p className="muted">Loading…</p>}
        {items && items.length === 0 && <p className="muted">No audit entries.</p>}
        {items && items.map(it => (
          <div key={it.id} style={{ borderBottom: "1px solid #233059", padding: "12px 0" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "baseline", flexWrap: "wrap" }}>
              <span className={`badge ${it.success ? "live" : "kill"}`}>{it.event_type}</span>
              <span className="muted">{new Date(it.created_at).toLocaleString()}</span>
              {it.message && <span className="muted">— {it.message}</span>}
            </div>
            {it.raw_command && <p style={{ margin: "6px 0" }}><strong>Command:</strong> {it.raw_command}</p>}
            {(it.parsed_payload || it.result_payload) && (
              <pre className="code">
                {JSON.stringify({ parsed: it.parsed_payload, result: it.result_payload }, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
