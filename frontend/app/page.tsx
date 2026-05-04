"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, getToken } from "../lib/api";
import type { OrderPreview, OrderResult, ParsedCommand } from "../lib/types";
import OrderPreviewCard from "../components/OrderPreviewCard";
import ConfirmationModal from "../components/ConfirmationModal";
import { TerminalIcon, PlayIcon, AlertIcon, CheckIcon } from "../components/Icons";

const EXAMPLES = [
  "Buy 1000 XRP at 0.55",
  "Sell 0.05 BTC at 65000",
  "Buy $500 worth of ETH at 3100",
  "Buy 5 AAPL at 180",
  "Sell 2 TSLA at 250",
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
      <h1 className="h1">
        <TerminalIcon /> Command
        <span className="h1-rule" />
      </h1>

      <div className="split">
        <div>
          <div className="card">
            <div className="card-head">
              <h2 className="h2">Natural-language input</h2>
              <span className="muted" style={{ fontSize: 11 }}>limit orders only · crypto + xStocks</span>
            </div>
            <textarea
              rows={3}
              placeholder="e.g. Buy 1000 XRP at 0.55"
              value={text}
              onChange={e => setText(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button onClick={handleParseOnly} disabled={busy || !text.trim()}>
                Parse only
              </button>
              <button className="primary" onClick={handlePreview} disabled={busy || !text.trim()}>
                <PlayIcon /> {busy ? "Working…" : "Preview / Run"}
              </button>
            </div>

            <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
              <span className="label" style={{ marginRight: 6 }}>Examples</span>
              {EXAMPLES.map((ex, i) => (
                <button key={i} className="chip" onClick={() => setText(ex)}>{ex}</button>
              ))}
            </div>
          </div>

          {err && (
            <div className="card danger">
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <AlertIcon className="icon lg" />
                <p className="danger-text" style={{ margin: 0, fontSize: 12 }}>{err}</p>
              </div>
            </div>
          )}

          {result && (
            <div className={`card ${result.success ? "ok" : "danger"}`}>
              <div className="card-head">
                <h2 className="h2">{result.success ? "Order processed" : "Order failed"}</h2>
                <span className={`badge ${result.dry_run ? "dry" : result.success ? "live" : "kill"}`}>
                  <span className={`dot ${result.dry_run ? "warn" : result.success ? "gain" : "loss"}`} />
                  {result.dry_run ? "Simulated" : result.success ? "Submitted" : "Failed"}
                </span>
              </div>
              {result.kraken_txid && (
                <p style={{ margin: "6px 0", fontSize: 12 }}>
                  <span className="label" style={{ marginRight: 6 }}>Kraken TXID</span>
                  <span className="num">{result.kraken_txid}</span>
                </p>
              )}
              {result.description && <p style={{ margin: "6px 0", fontSize: 12 }} className="dim">{result.description}</p>}
              {result.error && <p className="danger-text" style={{ fontSize: 12 }}>{result.error}</p>}
            </div>
          )}
        </div>

        <div>
          {parsed && (
            <div className="card">
              <div className="card-head">
                <h2 className="h2">Parsed</h2>
                <span className="badge info">
                  conf {(parsed.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="kv-grid">
                <div><div className="label">Intent</div><div className="value">{parsed.intent}</div></div>
                <div><div className="label">Side</div><div className="value">{parsed.side ?? <span className="muted">—</span>}</div></div>
                <div><div className="label">Asset</div><div className="value mono">{parsed.asset ?? <span className="muted">—</span>}</div></div>
                <div><div className="label">Quote</div><div className="value mono">{parsed.quote_currency ?? <span className="muted">—</span>}</div></div>
                <div><div className="label">Quantity</div><div className="value mono">{parsed.quantity ?? <span className="muted">—</span>}</div></div>
                <div><div className="label">Limit price</div><div className="value mono">{parsed.limit_price ?? <span className="muted">—</span>}</div></div>
              </div>
              {parsed.rejection_reason && (
                <p className="danger-text" style={{ marginTop: 12, fontSize: 12 }}>
                  {parsed.rejection_reason}
                </p>
              )}
              {parsed.warnings?.length > 0 && (
                <ul style={{ marginTop: 12, paddingLeft: 18, fontSize: 12 }}>
                  {parsed.warnings.map((w, i) => <li key={i} className="warn-text">{w}</li>)}
                </ul>
              )}
            </div>
          )}

          {preview && <OrderPreviewCard preview={preview} />}

          {!parsed && !preview && (
            <div className="card">
              <div className="empty">
                <TerminalIcon className="icon lg empty-icon" />
                <div>Type a command, then Parse or Preview.</div>
                <div style={{ fontSize: 11 }}>The risk engine validates before any order is sent.</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {showModal && preview && (
        <ConfirmationModal
          preview={preview}
          onCancel={() => setShowModal(false)}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  );
}
