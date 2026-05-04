"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { OpenOrder } from "../../lib/types";

export default function OpenOrdersPage() {
  const router = useRouter();
  const [items, setItems] = useState<OpenOrder[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    try {
      const r = await api.get<{ orders: OpenOrder[] }>("/kraken/open-orders");
      setItems(r.orders);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    refresh();
  }, [router]);

  async function cancel(txid: string) {
    if (!confirm(`Cancel order ${txid}?`)) return;
    try {
      await api.post("/kraken/cancel-order", { txid });
      refresh();
    } catch (e) {
      alert((e as Error).message);
    }
  }

  return (
    <div>
      <h1 className="h1">Open Orders</h1>
      <div className="card">
        <button onClick={refresh} disabled={busy} style={{ marginBottom: 12 }}>Refresh</button>
        {err && <p className="danger-text">{err}</p>}
        {items && items.length === 0 && <p className="muted">No open orders.</p>}
        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>TXID</th><th>Pair</th><th>Side</th><th>Type</th>
                <th>Volume</th><th>Price</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map(o => (
                <tr key={o.txid}>
                  <td>{o.txid}</td><td>{o.pair}</td><td>{o.side}</td><td>{o.order_type}</td>
                  <td>{o.volume}</td><td>{o.price}</td><td>{o.status}</td>
                  <td><button className="danger" onClick={() => cancel(o.txid)}>Cancel</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
