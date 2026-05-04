"use client";

import { useState } from "react";
import type { OrderPreview } from "../lib/types";
import { AlertIcon, CheckIcon, XIcon } from "./Icons";

interface Props {
  preview: OrderPreview;
  onCancel: () => void;
  onConfirm: (twoStep?: string) => Promise<void>;
}

export default function ConfirmationModal({ preview, onCancel, onConfirm }: Props) {
  const [twoStep, setTwoStep] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleConfirm() {
    setErr(null);
    setSubmitting(true);
    try {
      await onConfirm(preview.requires_two_step ? twoStep : undefined);
    } catch (e: unknown) {
      setErr((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="card-head">
          <h2 className="h2">Confirm order</h2>
          <span className={`badge ${preview.dry_run ? "dry" : "live"}`}>
            <span className={`dot ${preview.dry_run ? "warn" : "gain"}`} />
            {preview.dry_run ? "Dry-run" : "Live"}
          </span>
        </div>

        <div style={{
          fontFamily: "var(--font-mono)",
          fontSize: 14,
          padding: "12px 14px",
          background: "var(--bg-2)",
          border: "1px solid var(--border-faint)",
          borderRadius: "var(--radius-sm)",
          letterSpacing: "-0.01em",
        }}>
          <span className={preview.side === "buy" ? "side-buy" : "side-sell"} style={{ marginRight: 8 }}>
            {preview.side}
          </span>
          <span className="num">{preview.volume}</span>{" "}
          <span style={{ color: "var(--text-dim)" }}>{preview.pair}</span>{" "}
          {preview.trigger_price != null ? (
            <>
              <span style={{ color: "var(--text-mute)" }}>trigger</span>{" "}
              <span className="num">{preview.trigger_price}</span>{" "}
              <span style={{ color: "var(--text-mute)" }}>limit</span>{" "}
              <span className="num">{preview.limit_price}</span>{" "}
            </>
          ) : (
            <>
              <span style={{ color: "var(--text-mute)" }}>@</span>{" "}
              <span className="num">{preview.limit_price}</span>{" "}
            </>
          )}
          <span style={{ color: "var(--text-mute)" }}>·</span>{" "}
          <span className="num">{preview.notional_value.toFixed(2)}</span>{" "}
          <span style={{ color: "var(--text-mute)" }}>{preview.quote_currency}</span>
          {preview.order_type !== "limit" && (
            <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-mute)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              {preview.order_type}
            </div>
          )}
        </div>

        {preview.dry_run ? (
          <p className="warn-text" style={{ marginTop: 12, fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <AlertIcon /> Dry-run mode is enabled — this will be simulated only.
          </p>
        ) : (
          <p className="danger-text" style={{ marginTop: 12, fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <AlertIcon /> Real limit order on Kraken. There is no undo.
          </p>
        )}

        {preview.requires_two_step && (
          <div style={{ marginTop: 14, padding: 12, border: "1px solid var(--warn)", borderRadius: "var(--radius-sm)", background: "var(--warn-soft)" }}>
            <div className="label" style={{ color: "var(--warn)", marginBottom: 6 }}>Large order — two-step required</div>
            <p style={{ fontSize: 12, margin: "0 0 8px", color: "var(--text-dim)" }}>
              Type the phrase <strong style={{ fontFamily: "var(--font-mono)" }}>I CONFIRM</strong> to proceed.
            </p>
            <input
              placeholder="I CONFIRM"
              value={twoStep}
              onChange={e => setTwoStep(e.target.value)}
              autoFocus
            />
          </div>
        )}

        {err && <p className="danger-text" style={{ marginTop: 10, fontSize: 12 }}>{err}</p>}

        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
          <button className="ghost" onClick={onCancel} disabled={submitting}>
            <XIcon /> Cancel
          </button>
          <button className="primary" onClick={handleConfirm} disabled={submitting}>
            <CheckIcon /> {submitting ? "Placing…" : preview.dry_run ? "Simulate" : "Place order"}
          </button>
        </div>
      </div>
    </div>
  );
}
