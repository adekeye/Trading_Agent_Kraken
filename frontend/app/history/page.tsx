"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { HistoryOrder } from "../../lib/types";

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryOrder[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.get<{ orders: HistoryOrder[] }>("/kraken/order-history")
      .then(r => setItems(r.orders))
      .catch(e => setErr((e as Error).message));
  }, [router]);

  return (
    <div>
      <h1 className="h1">Order History</h1>
      <div className="card">
        {err && <p className="danger-text">{err}</p>}
        {!items && !err && <p className="muted">Loading…</p>}
        {items && items.length === 0 && <p className="muted">No closed orders.</p>}
        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>TXID</th><th>Pair</th><th>Side</th><th>Type</th>
                <th>Volume</th><th>Price</th><th>Status</th><th>Closed at</th>
              </tr>
            </thead>
            <tbody>
              {items.map(o => (
                <tr key={o.txid}>
                  <td>{o.txid}</td><td>{o.pair}</td><td>{o.side}</td><td>{o.order_type}</td>
                  <td>{o.volume}</td><td>{o.price}</td><td>{o.status}</td>
                  <td>{o.closed_at ? new Date(o.closed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
