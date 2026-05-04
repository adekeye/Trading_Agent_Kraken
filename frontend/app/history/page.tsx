"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { HistoryOrder } from "../../lib/types";
import { HistoryIcon, InboxIcon } from "../../components/Icons";

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
      <h1 className="h1"><HistoryIcon /> History <span className="h1-rule" /></h1>

      <div className="card">
        <div className="toolbar">
          <span className="stat">
            <span className="label">Closed</span>
            <span className="num">{items?.length ?? 0}</span>
          </span>
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
            <div>No closed orders yet.</div>
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
                <th>Closed at</th>
              </tr>
            </thead>
            <tbody>
              {items.map(o => (
                <tr key={o.txid}>
                  <td className="mono" style={{ color: "var(--text-dim)" }}>{o.txid}</td>
                  <td className="mono">{o.pair}</td>
                  <td><span className={o.side === "buy" ? "side-buy" : "side-sell"}>{o.side}</span></td>
                  <td className="dim">{o.order_type}</td>
                  <td className="num">{o.volume}</td>
                  <td className="num">{o.price}</td>
                  <td className="dim">{o.status}</td>
                  <td className="mono dim">{o.closed_at ? new Date(o.closed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
