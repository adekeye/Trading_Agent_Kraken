"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { BalanceItem } from "../../lib/types";

export default function BalancesPage() {
  const router = useRouter();
  const [items, setItems] = useState<BalanceItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.get<{ balances: BalanceItem[] }>("/kraken/balances")
      .then(r => setItems(r.balances))
      .catch(e => setErr((e as Error).message));
  }, [router]);

  return (
    <div>
      <h1 className="h1">Account Balances</h1>
      <div className="card">
        {err && <p className="danger-text">{err}</p>}
        {!items && !err && <p className="muted">Loading…</p>}
        {items && items.length === 0 && <p className="muted">No balances.</p>}
        {items && items.length > 0 && (
          <table>
            <thead>
              <tr><th>Asset</th><th>Amount</th></tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i}><td>{it.asset}</td><td>{it.amount}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
