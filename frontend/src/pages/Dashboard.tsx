import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarClock,
  IndianRupee,
  ShieldCheck,
  Upload,
  Wallet,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { inr, periodLabel } from "@/lib/format";
import type { Dashboard as DashboardData } from "@/lib/types";

export default function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/dashboard"),
  });

  if (isLoading || !data) return <Spinner />;

  return (
    <div>
      <PageHeader
        title={t("dashboard.title")}
        action={
          <button className="btn-primary" onClick={() => navigate("/invoices?upload=1")}>
            <Upload className="h-4 w-4" /> {t("dashboard.uploadInvoice")}
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <ScoreCard score={data.compliance_score} label={t("dashboard.complianceScore")} />
        <Kpi
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          label={t("dashboard.pendingReview")}
          value={String(data.invoices_pending_review)}
          onClick={() => navigate("/invoices?status_filter=needs_review")}
        />
        <Kpi
          icon={<CalendarClock className="h-5 w-5 text-brand-600" />}
          label={t("dashboard.nextDue")}
          value={
            data.next_due
              ? `${data.next_due.return_type} · ${data.days_to_next_due}d`
              : "—"
          }
          onClick={() => navigate("/returns")}
        />
        <Kpi
          icon={<IndianRupee className="h-5 w-5 text-accent-600" />}
          label={t("dashboard.taxLiability")}
          value={inr(data.estimated_tax_liability)}
        />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <Kpi
          icon={<Wallet className="h-5 w-5 text-accent-600" />}
          label={t("dashboard.itc")}
          value={inr(data.itc_available)}
        />
        <Kpi
          icon={<IndianRupee className="h-5 w-5 text-brand-600" />}
          label={t("dashboard.salesPeriod")}
          value={inr(data.sales_this_period)}
        />
        <Kpi
          icon={<IndianRupee className="h-5 w-5 text-slate-500" />}
          label={t("dashboard.purchasesPeriod")}
          value={inr(data.purchases_this_period)}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Compliance calendar */}
        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-800">{t("dashboard.upcoming")}</h3>
          <div className="space-y-2">
            {data.upcoming_due_dates.length === 0 && (
              <p className="text-sm text-slate-400">—</p>
            )}
            {data.upcoming_due_dates.map((d) => {
              const overdue = d.days_remaining < 0;
              return (
                <div
                  key={`${d.return_type}-${d.period}`}
                  className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2.5"
                >
                  <div>
                    <p className="text-sm font-medium">
                      {d.return_type} · {periodLabel(d.period)}
                    </p>
                    <p className="text-xs text-slate-400">{d.due_date}</p>
                  </div>
                  <span
                    className={`badge ${
                      overdue
                        ? "bg-red-50 text-red-700"
                        : d.days_remaining <= 3
                          ? "bg-amber-50 text-amber-700"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {overdue
                      ? t("dashboard.overdue")
                      : t("dashboard.daysLeft", { count: d.days_remaining })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-800">{t("dashboard.recent")}</h3>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-slate-400">{t("dashboard.noActivity")}</p>
          ) : (
            <div className="space-y-2">
              {data.recent_activity.map((a, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span
                      className={`badge ${
                        a.type === "sales"
                          ? "bg-accent-50 text-accent-700"
                          : "bg-brand-50 text-brand-700"
                      }`}
                    >
                      {a.type}
                    </span>
                    <span className="text-slate-600">{a.party || "—"}</span>
                  </div>
                  <span className="font-medium">{inr(a.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`card flex flex-col items-start gap-2 text-left ${onClick ? "hover:border-brand-300" : "cursor-default"}`}
    >
      {icon}
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-lg font-bold text-slate-900">{value}</span>
    </button>
  );
}

function ScoreCard({ score, label }: { score: number; label: string }) {
  const color = score >= 75 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";
  const data = [
    { value: score, fill: color },
    { value: 100 - score, fill: "#e2e8f0" },
  ];
  return (
    <div className="card flex items-center gap-3">
      <div className="relative h-16 w-16">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              innerRadius={22}
              outerRadius={32}
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >
              {data.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
          {score}
        </span>
      </div>
      <div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <ShieldCheck className="h-4 w-4 text-accent-600" />
          {label}
        </div>
      </div>
    </div>
  );
}
