"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { OpenOrder } from "../../lib/types";
import { ListIcon, RefreshIcon, XIcon, InboxIcon } from "../../components/Icons";

export default function OpenOrdersPage() {
  const router = useRouter();
  const [items, setItems] = useState<OpenOrder[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    setErr(null);
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
      <h1 className="h1"><ListIcon /> Open orders <span className="h1-rule" /></h1>

      <div className="card">
        <div className="toolbar">
          <span className="stat">
            <span className="label">Open</span>
            <span className="num">{items?.length ?? 0}</span>
          </span>
          <div className="grow" />
          <button onClick={refresh} disabled={busy}>
            <RefreshIcon /> {busy ? "Loading…" : "Refresh"}
          </button>
        </div>

        {err && <p className="danger-text" style={{ fontSize: 12 }}>{err}</p>}

        {!items && !err && (
          <div>
            <span className="skel row-line" style={{ width: "100%" }} />
            <span className="skel row-line" style={{ width: "85%" }} />
          </div>
        )}

        {items && items.length === 0 && (
          <div className="empty">
            <InboxIcon className="icon lg empty-icon" />
            <div>No open orders.</div>
          </div>
        )}

        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>TXID</th>
                <th>Pair</th>
                <th>Side</th>
                <th>Type</th>
                <th className="num">Volume</th>
                <th className="num">Price</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map(o => (
                <tr key={o.txid}>
                  <td className="mono" style={{ color: "var(--text-dim)" }}>{o.txid}</td>
                  <td className="mono">{o.pair}</td>
                  <td>
                    <span className={o.side === "buy" ? "side-buy" : "side-sell"}>{o.side}</span>
                  </td>
                  <td className="dim">{o.order_type}</td>
                  <td className="num">{o.volume}</td>
                  <td className="num">{o.price}</td>
                  <td>
                    <span className="badge info"><span className="dot info" /> {o.status}</span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="danger" onClick={() => cancel(o.txid)}>
                      <XIcon /> Cancel
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
