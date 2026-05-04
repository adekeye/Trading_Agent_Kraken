"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { AuditLog } from "../../lib/types";
import { ShieldIcon, InboxIcon, CheckIcon, AlertIcon } from "../../components/Icons";

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
      <h1 className="h1"><ShieldIcon /> Audit log <span className="h1-rule" /></h1>

      <div className="card">
        <div className="toolbar">
          <span className="stat">
            <span className="label">Events</span>
            <span className="num">{items?.length ?? 0}</span>
          </span>
        </div>

        {err && <p className="danger-text" style={{ fontSize: 12 }}>{err}</p>}

        {!items && !err && (
          <div>
            <span className="skel box" style={{ marginBottom: 8 }} />
            <span className="skel box" />
          </div>
        )}

        {items && items.length === 0 && (
          <div className="empty">
            <InboxIcon className="icon lg empty-icon" />
            <div>No audit events yet.</div>
          </div>
        )}

        {items && items.map(it => (
          <div key={it.id} style={{ borderBottom: "1px solid var(--border-faint)", padding: "10px 0" }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", fontSize: 12 }}>
              <span className={`badge ${it.success ? "live" : "kill"}`}>
                {it.success ? <CheckIcon /> : <AlertIcon />} {it.event_type}
              </span>
              <span className="muted mono" style={{ fontSize: 11 }}>
                {new Date(it.created_at).toLocaleString()}
              </span>
              {it.message && <span className="dim">— {it.message}</span>}
            </div>
            {it.raw_command && (
              <p style={{ margin: "6px 0", fontSize: 12 }} className="mono">
                <span className="label" style={{ marginRight: 6 }}>cmd</span>
                {it.raw_command}
              </p>
            )}
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
