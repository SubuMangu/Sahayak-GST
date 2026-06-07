import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import type { Plan, Subscription } from "@/lib/types";

export default function Billing() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");

  const { data: plans } = useQuery({ queryKey: ["plans"], queryFn: () => api.get<Plan[]>("/billing/plans") });
  const { data: sub, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api.get<Subscription>("/billing/subscription"),
  });

  const subscribe = useMutation({
    mutationFn: async (plan: string) => {
      const order = await api.post<{ order_id: string }>("/billing/checkout", { plan });
      // Mock flow: confirm immediately. In live mode, open Razorpay checkout here.
      return api.post<Subscription>("/billing/confirm", { order_id: order.order_id, plan });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subscription"] });
      setMsg(t("billing.activated"));
      setTimeout(() => setMsg(""), 3000);
    },
  });

  if (isLoading || !sub || !plans) return <Spinner />;

  const usagePct = Math.min(100, Math.round((sub.scans_used / Math.max(sub.scan_limit, 1)) * 100));

  return (
    <div>
      <PageHeader title={t("billing.title")} />
      {msg && (
        <div className="mb-4 rounded-xl border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-700">
          {msg}
        </div>
      )}

      <div className="card mb-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500">{t("billing.currentPlan")}</p>
            <p className="text-xl font-bold capitalize text-slate-900">{sub.plan}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500">{t("billing.scansUsed")}</p>
            <p className="font-semibold">
              {sub.scans_used} / {sub.scan_limit}
            </p>
          </div>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full ${usagePct > 90 ? "bg-red-500" : "bg-brand-600"}`}
            style={{ width: `${usagePct}%` }}
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((p) => {
          const isCurrent = p.code === sub.plan;
          return (
            <div
              key={p.code}
              className={`card flex flex-col ${
                p.code === "pro" ? "ring-2 ring-brand-600" : ""
              }`}
            >
              <h3 className="text-lg font-bold capitalize">{p.name}</h3>
              <p className="mt-1">
                <span className="text-3xl font-bold">{inr(p.price_inr)}</span>
                <span className="text-sm text-slate-400">/{t("billing.month")}</span>
              </p>
              <ul className="mt-4 flex-1 space-y-2 text-sm text-slate-600">
                {p.features.map((f, i) => (
                  <li key={i} className="flex gap-2">
                    <Check className="h-4 w-4 shrink-0 text-accent-600" /> {f}
                  </li>
                ))}
              </ul>
              <button
                className={isCurrent ? "btn-secondary mt-4" : "btn-primary mt-4"}
                disabled={isCurrent || p.code === "free" || subscribe.isPending}
                onClick={() => subscribe.mutate(p.code)}
              >
                {isCurrent ? t("billing.current") : t("billing.choose", { plan: p.name })}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
