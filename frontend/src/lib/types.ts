export interface Business {
  id: string;
  legal_name: string;
  trade_name?: string | null;
  gstin?: string | null;
  scheme: string;
  state_code?: string | null;
  address?: string | null;
  role?: string | null;
}

export interface LineItem {
  description?: string | null;
  hsn?: string | null;
  qty?: number | null;
  rate?: number | null;
  taxable_value: number;
  gst_rate: number;
}

export interface Anomaly {
  code: string;
  field: string;
  severity: "low" | "medium" | "high";
  message: string;
}

export interface InvoiceListItem {
  id: string;
  direction: string;
  status: string;
  source: string;
  counterparty_name?: string | null;
  counterparty_gstin?: string | null;
  invoice_no?: string | null;
  invoice_date?: string | null;
  taxable_value: number;
  total_value: number;
  overall_confidence: number;
  needs_accountant_review: boolean;
  created_at: string;
}

export interface InvoiceDetail extends InvoiceListItem {
  place_of_supply?: string | null;
  cgst: number;
  sgst: number;
  igst: number;
  cess: number;
  line_items?: LineItem[] | null;
  confidence?: Record<string, number> | null;
  anomalies?: Anomaly[] | null;
  file_name?: string | null;
  file_mime?: string | null;
  notes?: string | null;
}

export interface DueItem {
  return_type: string;
  period: string;
  due_date: string;
  days_remaining: number;
}

export interface Dashboard {
  compliance_score: number;
  invoices_pending_review: number;
  next_due?: DueItem | null;
  days_to_next_due?: number | null;
  estimated_tax_liability: number;
  itc_available: number;
  itc_claimed: number;
  upcoming_due_dates: DueItem[];
  sales_this_period: number;
  purchases_this_period: number;
  recent_activity: { type: string; party?: string; amount: number; date?: string }[];
}

export interface GSTRFiling {
  id: string;
  return_type: string;
  period: string;
  status: string;
  summary?: Record<string, unknown> | null;
  is_nil: boolean;
}

export interface Plan {
  code: string;
  name: string;
  price_inr: number;
  monthly_scans: number;
  features: string[];
}

export interface Subscription {
  plan: string;
  status: string;
  scans_used: number;
  scan_limit: number;
  invoices_processed: number;
  topup_scans: number;
  current_period_end?: string | null;
}

export interface ReconRun {
  id: string;
  source: string;
  period: string;
  summary?: Record<string, number> | null;
}

export interface ReconItem {
  id: string;
  match_status: string;
  supplier_gstin?: string | null;
  invoice_no?: string | null;
  tax_diff: number;
  books_data?: Record<string, number> | null;
  portal_data?: Record<string, number> | null;
  resolution?: string | null;
}

export interface AppNotification {
  id: string;
  category: string;
  title: string;
  body: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
}
