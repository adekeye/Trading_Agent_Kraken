"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "../../lib/api";
import type { UserSettings } from "../../lib/types";
import { SettingsIcon, CheckIcon } from "../../components/Icons";

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
      <div>
        <h1 className="h1"><SettingsIcon /> Settings <span className="h1-rule" /></h1>
        <div className="card">
          {err ? <p className="danger-text" style={{ fontSize: 12 }}>{err}</p> : (
            <>
              <span className="skel row-line" style={{ width: "60%" }} />
              <span className="skel row-line" style={{ width: "40%" }} />
            </>
          )}
        </div>
      </div>
    );
  }

  const Toggle = ({ checked, onChange, danger }: { checked: boolean; onChange: (v: boolean) => void; danger?: boolean }) => (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      style={{
        width: 44, height: 22, padding: 0, position: "relative",
        background: checked ? (danger ? "var(--loss)" : "var(--accent)") : "var(--bg-3)",
        borderColor: checked ? (danger ? "var(--loss)" : "var(--accent)") : "var(--border)",
      }}
    >
      <span style={{
        position: "absolute",
        top: 2, left: checked ? 24 : 2,
        width: 16, height: 16,
        background: "var(--bg-0)",
        borderRadius: 999,
        transition: "left 120ms ease",
      }} />
    </button>
  );

  const Field = ({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) => (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "10px 0", borderBottom: "1px solid var(--border-faint)", gap: 16,
    }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 13, color: "var(--text)" }}>{label}</div>
        {hint && <div style={{ fontSize: 11, color: "var(--text-mute)" }}>{hint}</div>}
      </div>
      <div style={{ flexShrink: 0 }}>{children}</div>
    </div>
  );

  return (
    <div>
      <h1 className="h1"><SettingsIcon /> Settings <span className="h1-rule" /></h1>

      <div className="card" style={{ maxWidth: 720 }}>
        <h2 className="h2">Trading guard rails</h2>

        <Field label="Dry-run mode" hint="Simulate orders without calling Kraken.">
          <Toggle checked={s.dry_run} onChange={v => setS({ ...s, dry_run: v })} />
        </Field>

        <Field label="Trading enabled" hint="Master kill switch — blocks every order when off.">
          <Toggle
            checked={s.trading_enabled}
            onChange={v => setS({ ...s, trading_enabled: v })}
            danger={!s.trading_enabled}
          />
        </Field>

        <Field label={`Max order notional (${s.preferred_quote_currency})`} hint="Per-order cap; risk engine rejects anything larger.">
          <input
            type="number"
            value={s.max_order_notional_usd}
            min={0}
            step={50}
            style={{ width: 140, textAlign: "right", fontFamily: "var(--font-mono)" }}
            onChange={e => setS({ ...s, max_order_notional_usd: parseFloat(e.target.value) || 0 })}
          />
        </Field>

        <Field label="Preferred quote currency">
          <select
            value={s.preferred_quote_currency}
            onChange={e => setS({ ...s, preferred_quote_currency: e.target.value })}
            style={{ width: 140 }}
          >
            {["USD", "USDT", "USDC", "EUR", "GBP"].map(q => <option key={q}>{q}</option>)}
          </select>
        </Field>

        <Field label="Two-step confirmation for large orders" hint="Type 'I CONFIRM' before large orders are placed.">
          <Toggle
            checked={s.require_two_step_for_large_orders}
            onChange={v => setS({ ...s, require_two_step_for_large_orders: v })}
          />
        </Field>

        <Field label={`Large order threshold (${s.preferred_quote_currency})`} hint="Notional at or above this triggers two-step.">
          <input
            type="number"
            value={s.large_order_threshold_usd}
            min={0}
            step={100}
            style={{ width: 140, textAlign: "right", fontFamily: "var(--font-mono)" }}
            onChange={e => setS({ ...s, large_order_threshold_usd: parseFloat(e.target.value) || 0 })}
          />
        </Field>

        <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 16 }}>
          <button className="primary" onClick={save}>
            <CheckIcon /> Save
          </button>
          {msg && <span className="ok-text" style={{ fontSize: 12 }}>{msg}</span>}
          {err && <span className="danger-text" style={{ fontSize: 12 }}>{err}</span>}
        </div>
      </div>
    </div>
  );
}
