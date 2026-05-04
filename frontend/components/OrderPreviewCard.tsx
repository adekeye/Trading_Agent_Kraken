"use client";

import type { OrderPreview } from "../lib/types";
import { ClockIcon, AlertIcon } from "./Icons";

export default function OrderPreviewCard({ preview }: { preview: OrderPreview }) {
  const expires = new Date(preview.expires_at);
  return (
    <div className={`card ${preview.requires_two_step ? "warn" : ""}`}>
      <div className="card-head">
        <h2 className="h2">Order preview</h2>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className={`badge ${preview.dry_run ? "dry" : "live"}`}>
            <span className={`dot ${preview.dry_run ? "warn" : "gain"}`} />
            {preview.dry_run ? "Dry-run" : "Live"}
          </span>
          {preview.requires_two_step && (
            <span className="badge kill"><AlertIcon /> Two-step</span>
          )}
        </div>
      </div>

      <div className="kv-grid" style={{ marginBottom: 8 }}>
        <div>
          <div className="label">Pair</div>
          <div className="value mono">{preview.pair}</div>
        </div>
        <div>
          <div className="label">Side</div>
          <div className={preview.side === "buy" ? "side-buy" : "side-sell"}>
            {preview.side}
          </div>
        </div>
        <div>
          <div className="label">Type</div>
          <div className="value">limit</div>
        </div>
        <div>
          <div className="label">Quantity</div>
          <div className="value mono">{preview.volume}</div>
        </div>
        <div>
          <div className="label">Limit price</div>
          <div className="value mono">{preview.limit_price}</div>
        </div>
        <div>
          <div className="label">Notional · {preview.quote_currency}</div>
          <div className="value mono">{preview.notional_value.toFixed(2)}</div>
        </div>
        {preview.fees_estimate !== null && preview.fees_estimate !== undefined && (
          <div>
            <div className="label">Fees est.</div>
            <div className="value mono">{preview.fees_estimate}</div>
          </div>
        )}
      </div>

      {preview.warnings?.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border-faint)" }}>
          <div className="label" style={{ marginBottom: 6 }}>Warnings</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {preview.warnings.map((w, i) => (
              <li key={i} className="warn-text" style={{ fontSize: 12 }}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 10, fontSize: 11, color: "var(--text-mute)", display: "inline-flex", alignItems: "center", gap: 6 }}>
        <ClockIcon /> Confirmation expires {expires.toLocaleTimeString()}
      </div>
    </div>
  );
}
