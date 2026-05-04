"use client";

import { useState } from "react";
import type { OrderPreview } from "../lib/types";

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
        <h2 className="h2">Confirm order</h2>
        <p>
          {preview.side.toUpperCase()} {preview.volume} {preview.pair} @ {preview.limit_price}
          {" "} ({preview.notional_value.toFixed(2)} {preview.quote_currency})
        </p>
        {preview.dry_run ? (
          <p className="warn-text">Dry-run mode is enabled — this will be simulated only.</p>
        ) : (
          <p className="danger-text">
            ⚠ This will place a <strong>real</strong> limit order on Kraken. There is no undo.
          </p>
        )}
        {preview.requires_two_step && (
          <div style={{ marginTop: 12 }}>
            <p className="warn-text">
              Large order: type the phrase <strong>I CONFIRM</strong> to proceed.
            </p>
            <input
              placeholder="I CONFIRM"
              value={twoStep}
              onChange={e => setTwoStep(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
        )}
        {err && <p className="danger-text">{err}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
          <button className="ghost" onClick={onCancel} disabled={submitting}>Cancel</button>
          <button className="primary" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Placing…" : (preview.dry_run ? "Simulate" : "Place order")}
          </button>
        </div>
      </div>
    </div>
  );
}
