"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, getToken } from "../lib/api";
import type { OrderPreview, OrderResult, ParsedCommand } from "../lib/types";
import OrderPreviewCard from "../components/OrderPreviewCard";
import ConfirmationModal from "../components/ConfirmationModal";

const EXAMPLES = [
  "Buy 1000 XRP at 0.55",
  "Sell 0.05 BTC at 65000",
  "Buy $500 worth of ETH at 3100",
  "Show my balances",
  "Show open orders",
  "Cancel order OABC-123",
];

export default function TradePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<ParsedCommand | null>(null);
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [result, setResult] = useState<OrderResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!getToken()) router.push("/login");
  }, [router]);

  async function handleParseOnly() {
    setErr(null); setResult(null); setPreview(null);
    setBusy(true);
    try {
      const p = await api.post<ParsedCommand>("/commands/parse", { text });
      setParsed(p);
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handlePreview() {
    setErr(null); setResult(null); setPreview(null);
    setBusy(true);
    try {
      const p = await api.post<ParsedCommand>("/commands/parse", { text });
      setParsed(p);
      if (p.intent === "place_order" && !p.rejection_reason) {
        const pv = await api.post<OrderPreview>("/commands/preview", { text });
        setPreview(pv);
        setShowModal(true);
      } else if (p.intent === "show_balances") {
        router.push("/balances");
      } else if (p.intent === "show_orders") {
        router.push("/orders");
      } else if (p.intent === "show_history") {
        router.push("/history");
      } else if (p.intent === "cancel_order" && p.cancel_txid) {
        const r = await api.post("/kraken/cancel-order", { txid: p.cancel_txid });
        setResult({ success: true, dry_run: false, description: `Cancel submitted for ${p.cancel_txid}`, raw_response: r } as unknown as OrderResult);
      } else if (p.rejection_reason) {
        setErr(p.rejection_reason);
      }
    } catch (e: unknown) {
      if (e instanceof ApiError) setErr(e.message);
      else setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm(twoStep?: string) {
    if (!preview) return;
    const r = await api.post<OrderResult>("/commands/confirm", {
      confirmation_id: preview.confirmation_id,
      confirm: true,
      second_factor_phrase: twoStep,
    });
    setResult(r);
    setShowModal(false);
    setPreview(null);
  }

  return (
    <div>
      <h1 className="h1">Trade with words</h1>
      <p className="muted">
        Type a natural-language command. The app will parse it, validate it, and require explicit
        confirmation before placing a limit order. Only Kraken-supported crypto pairs are allowed.
      </p>

      <div className="card">
        <textarea
          rows={3}
          placeholder="e.g. Buy 1000 XRP at 0.55"
          value={text}
          onChange={e => setText(e.target.value)}
          style={{ width: "100%" }}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button onClick={handleParseOnly} disabled={busy || !text.trim()}>Parse only</button>
          <button className="primary" onClick={handlePreview} disabled={busy || !text.trim()}>
            {busy ? "Working…" : "Preview / Run"}
          </button>
        </div>
        <div style={{ marginTop: 12 }}>
          <span className="muted">Examples: </span>
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              className="ghost"
              style={{ marginRight: 4, marginBottom: 4 }}
              onClick={() => setText(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="card danger"><p className="danger-text">{err}</p></div>}

      {parsed && (
        <div className="card">
          <h2 className="h2">Parsed</h2>
          <div className="row">
            <div><div className="label">Intent</div><div className="value">{parsed.intent}</div></div>
            <div><div className="label">Side</div><div className="value">{parsed.side ?? "—"}</div></div>
            <div><div className="label">Asset</div><div className="value">{parsed.asset ?? "—"}</div></div>
            <div><div className="label">Quote</div><div className="value">{parsed.quote_currency ?? "—"}</div></div>
            <div><div className="label">Quantity</div><div className="value">{parsed.quantity ?? "—"}</div></div>
            <div><div className="label">Limit price</div><div className="value">{parsed.limit_price ?? "—"}</div></div>
            <div><div className="label">Confidence</div><div className="value">{parsed.confidence.toFixed(2)}</div></div>
          </div>
          {parsed.rejection_reason && <p className="danger-text" style={{ marginTop: 12 }}>{parsed.rejection_reason}</p>}
          {parsed.warnings?.length > 0 && (
            <ul style={{ marginTop: 12 }}>
              {parsed.warnings.map((w, i) => <li key={i} className="warn-text">{w}</li>)}
            </ul>
          )}
        </div>
      )}

      {preview && <OrderPreviewCard preview={preview} />}

      {showModal && preview && (
        <ConfirmationModal
          preview={preview}
          onCancel={() => setShowModal(false)}
          onConfirm={handleConfirm}
        />
      )}

      {result && (
        <div className={`card ${result.success ? "ok" : "danger"}`}>
          <h2 className="h2">{result.success ? "Order processed" : "Order failed"}</h2>
          {result.dry_run && <p className="warn-text">Dry-run simulation — no order was sent.</p>}
          {result.kraken_txid && <p>Kraken TXID: <strong>{result.kraken_txid}</strong></p>}
          {result.description && <p>{result.description}</p>}
          {result.error && <p className="danger-text">{result.error}</p>}
        </div>
      )}
    </div>
  );
}
