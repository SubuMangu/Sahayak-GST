// Indian number formatting (lakh/crore grouping) for money displays.
export function inr(value: number | null | undefined): string {
  const v = value ?? 0;
  return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

export function periodLabel(period: string): string {
  const months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const mm = parseInt(period.slice(0, 2), 10);
  return `${months[mm]} ${period.slice(2)}`;
}

export function currentPeriod(): string {
  const now = new Date();
  // Most recent completed month.
  let m = now.getMonth(); // 0-based current month -> previous completed = m (since getMonth is 0-based for current)
  let y = now.getFullYear();
  if (m === 0) {
    m = 12;
    y -= 1;
  }
  return `${String(m).padStart(2, "0")}${y}`;
}

export function confidenceColor(score: number): string {
  if (score >= 0.85) return "bg-accent-50 text-accent-700";
  if (score >= 0.6) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

export function statusBadge(status: string): { label: string; cls: string } {
  switch (status) {
    case "confirmed":
      return { label: "Confirmed", cls: "bg-accent-50 text-accent-700" };
    case "needs_review":
      return { label: "Needs Review", cls: "bg-amber-50 text-amber-700" };
    case "processing":
      return { label: "Processing", cls: "bg-brand-50 text-brand-700" };
    case "failed":
      return { label: "Failed", cls: "bg-red-50 text-red-700" };
    case "ready_for_filing":
      return { label: "Ready", cls: "bg-accent-50 text-accent-700" };
    case "filed":
      return { label: "Filed", cls: "bg-brand-50 text-brand-700" };
    default:
      return { label: status, cls: "bg-slate-100 text-slate-600" };
  }
}
