"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { BalanceItem } from "../../lib/types";
import { WalletIcon, RefreshIcon, InboxIcon } from "../../components/Icons";

export default function BalancesPage() {
  const router = useRouter();
  const [items, setItems] = useState<BalanceItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function load() {
    setLoading(true);
    api.get<{ balances: BalanceItem[] }>("/kraken/balances")
      .then(r => setItems(r.balances))
      .catch(e => setErr((e as Error).message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    load();
  }, [router]);

  const total = items?.reduce((acc, it) => acc + (Number.isFinite(it.amount) ? it.amount : 0), 0) ?? 0;

  return (
    <div>
      <h1 className="h1"><WalletIcon /> Balances <span className="h1-rule" /></h1>

      <div className="card">
        <div className="toolbar">
          <span className="stat"><span className="label">Assets</span><span className="num">{items?.length ?? 0}</span></span>
          <span className="stat"><span className="label">Σ Units</span><span className="num">{total.toLocaleString(undefined, { maximumFractionDigits: 8 })}</span></span>
          <div className="grow" />
          <button onClick={load} disabled={loading}>
            <RefreshIcon /> {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {err && <p className="danger-text" style={{ fontSize: 12 }}>{err}</p>}

        {!items && !err && (
          <div>
            <span className="skel row-line" style={{ width: "60%" }} />
            <span className="skel row-line" style={{ width: "40%" }} />
            <span className="skel row-line" style={{ width: "70%" }} />
          </div>
        )}

        {items && items.length === 0 && (
          <div className="empty">
            <InboxIcon className="icon lg empty-icon" />
            <div>No balances on this account.</div>
          </div>
        )}

        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i}>
                  <td className="mono">{it.asset}</td>
                  <td className="num">{it.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
