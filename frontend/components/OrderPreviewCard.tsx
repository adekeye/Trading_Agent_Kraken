"use client";

import type { OrderPreview } from "../lib/types";

export default function OrderPreviewCard({ preview }: { preview: OrderPreview }) {
  return (
    <div className={`card ${preview.requires_two_step ? "warn" : ""}`}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 className="h2">Order preview</h2>
        <span className={`badge ${preview.dry_run ? "dry" : "live"}`}>
          {preview.dry_run ? "DRY-RUN" : "LIVE"}
        </span>
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <div>
          <div className="label">Pair</div>
          <div className="value">{preview.pair}</div>
        </div>
        <div>
          <div className="label">Side</div>
          <div className="value" style={{ textTransform: "uppercase" }}>{preview.side}</div>
        </div>
        <div>
          <div className="label">Order type</div>
          <div className="value">limit</div>
        </div>
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <div>
          <div className="label">Quantity</div>
          <div className="value">{preview.volume}</div>
        </div>
        <div>
          <div className="label">Limit price</div>
          <div className="value">{preview.limit_price}</div>
        </div>
        <div>
          <div className="label">Notional ({preview.quote_currency})</div>
          <div className="value">{preview.notional_value.toFixed(2)}</div>
        </div>
      </div>

      {preview.fees_estimate !== null && preview.fees_estimate !== undefined && (
        <div style={{ marginTop: 8 }}>
          <span className="label">Fees estimate: </span>
          <span>{preview.fees_estimate}</span>
        </div>
      )}

      {preview.warnings?.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="label">Warnings</div>
          <ul style={{ margin: 0 }}>
            {preview.warnings.map((w, i) => (
              <li key={i} className="warn-text">{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <span className="muted">Confirmation expires at:</span>{" "}
        <span>{new Date(preview.expires_at).toLocaleTimeString()}</span>
      </div>
    </div>
  );
}
