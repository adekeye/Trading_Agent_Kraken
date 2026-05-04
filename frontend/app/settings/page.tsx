"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { UserSettings } from "../../lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [s, setS] = useState<UserSettings | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    api.get<UserSettings>("/settings").then(setS).catch(e => setErr((e as Error).message));
  }, [router]);

  async function save() {
    if (!s) return;
    setErr(null); setMsg(null);
    try {
      const updated = await api.put<UserSettings>("/settings", s);
      setS(updated);
      setMsg("Saved.");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (!s) {
    return (
      <div className="card">
        {err ? <p className="danger-text">{err}</p> : <p className="muted">Loading settings…</p>}
      </div>
    );
  }

  return (
    <div>
      <h1 className="h1">Settings</h1>
      <div className="card">
        <h2 className="h2">Trading guard rails</h2>
        <div style={{ display: "grid", gap: 12, maxWidth: 520 }}>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>
              Dry-run mode <span className="muted">(simulates orders without calling Kraken)</span>
            </span>
            <input
              type="checkbox"
              checked={s.dry_run}
              onChange={e => setS({ ...s, dry_run: e.target.checked })}
            />
          </label>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>
              Trading enabled <span className="muted">(global kill switch)</span>
            </span>
            <input
              type="checkbox"
              checked={s.trading_enabled}
              onChange={e => setS({ ...s, trading_enabled: e.target.checked })}
            />
          </label>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Max order notional ({s.preferred_quote_currency})</span>
            <input
              type="number"
              value={s.max_order_notional_usd}
              min={0}
              step={50}
              onChange={e => setS({ ...s, max_order_notional_usd: parseFloat(e.target.value) || 0 })}
            />
          </label>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Preferred quote currency</span>
            <select
              value={s.preferred_quote_currency}
              onChange={e => setS({ ...s, preferred_quote_currency: e.target.value })}
            >
              {["USD", "USDT", "USDC", "EUR", "GBP"].map(q => <option key={q}>{q}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Two-step confirmation for large orders</span>
            <input
              type="checkbox"
              checked={s.require_two_step_for_large_orders}
              onChange={e => setS({ ...s, require_two_step_for_large_orders: e.target.checked })}
            />
          </label>
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Large order threshold ({s.preferred_quote_currency})</span>
            <input
              type="number"
              value={s.large_order_threshold_usd}
              min={0}
              step={100}
              onChange={e => setS({ ...s, large_order_threshold_usd: parseFloat(e.target.value) || 0 })}
            />
          </label>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="primary" onClick={save}>Save</button>
        </div>
        {msg && <p className="ok-text">{msg}</p>}
        {err && <p className="danger-text">{err}</p>}
      </div>
    </div>
  );
}
