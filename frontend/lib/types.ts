export type Intent =
  | "place_order"
  | "cancel_order"
  | "show_orders"
  | "show_balances"
  | "show_history"
  | "unknown";

export type OrderType = "limit" | "stop-loss-limit" | "take-profit-limit";

export interface ParsedCommand {
  intent: Intent;
  side?: "buy" | "sell" | null;
  asset?: string | null;
  quote_currency?: string | null;
  quantity?: number | null;
  notional_amount?: number | null;
  limit_price?: number | null;
  trigger_price?: number | null;
  order_type?: OrderType | null;
  cancel_txid?: string | null;
  confidence: number;
  requires_confirmation: boolean;
  rejection_reason?: string | null;
  warnings: string[];
}

export interface OrderPreview {
  confirmation_id: string;
  pair: string;
  side: "buy" | "sell";
  order_type: OrderType;
  volume: number;
  limit_price: number;
  trigger_price?: number | null;
  notional_value: number;
  quote_currency: string;
  fees_estimate: number | null;
  dry_run: boolean;
  requires_two_step: boolean;
  warnings: string[];
  expires_at: string;
}

export interface OrderResult {
  success: boolean;
  dry_run: boolean;
  kraken_txid?: string | null;
  description?: string | null;
  error?: string | null;
}

export interface UserSettings {
  dry_run: boolean;
  trading_enabled: boolean;
  max_order_notional_usd: number;
  preferred_quote_currency: string;
  require_two_step_for_large_orders: boolean;
  large_order_threshold_usd: number;
}

export interface BalanceItem { asset: string; amount: number; }
export interface OpenOrder {
  txid: string; pair: string; side: string; order_type: string;
  volume: number; price: number; status: string; opened_at?: string | null;
}
export interface HistoryOrder {
  txid: string; pair: string; side: string; order_type: string;
  volume: number; price: number; status: string; closed_at?: string | null;
}
export interface AuditLog {
  id: number; event_type: string; raw_command: string | null;
  parsed_payload: Record<string, unknown> | null;
  result_payload: Record<string, unknown> | null;
  success: boolean; message: string | null; created_at: string;
}

export interface EquitiesStatus {
  fetched_at: string | null;
  ticker_count: number;
  using_fallback: boolean;
  last_error: string | null;
  tickers: string[];
}
