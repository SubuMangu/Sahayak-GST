import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitCompareArrows, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { currentPeriod, inr, periodLabel } from "@/lib/format";
import type { ReconItem, ReconRun } from "@/lib/types";

export default function Reconciliation() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [period, setPeriod] = useState(currentPeriod());
  const [run, setRun] = useState<ReconRun | null>(null);
  const [error, setError] = useState("");

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<ReconRun>(
        `/compliance/reconcile?period=${period}&source=2B`,
        form
      );
    },
    onSuccess: (r) => {
      setRun(r);
      setError("");
      qc.invalidateQueries({ queryKey: ["recon-items", r.id] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  const { data: items, isLoading } = useQuery({
    queryKey: ["recon-items", run?.id],
    queryFn: () => api.get<ReconItem[]>(`/compliance/reconcile/${run!.id}/items`),
    enabled: !!run,
  });

  const resolve = useMutation({
    mutationFn: ({ itemId, resolution }: { itemId: string; resolution: string }) =>
      api.post(`/compliance/reconcile/items/${itemId}/resolve`, { resolution }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recon-items", run?.id] }),
  });

  const s = run?.summary ?? {};

  return (
    <div>
      <PageHeader title={t("recon.title")} />
      <p className="mb-4 text-sm text-slate-500">{t("recon.subtitle")}</p>
      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      <div className="card mb-5 flex flex-wrap items-end gap-3">
        <div>
          <label className="label">{t("returns.period")}</label>
          <input
            className="input"
            value={periodLabel(period)}
            readOnly
            onClick={() => {}}
          />
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])}
        />
        <button
          className="btn-primary"
          onClick={() => fileRef.current?.click()}
          disabled={upload.isPending}
        >
          <Upload className="h-4 w-4" /> {upload.isPending ? "…" : t("recon.upload")}
        </button>
      </div>

      {run && (
        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label={t("recon.matched")} value={String(s.matched ?? 0)} cls="text-accent-700" />
          <Stat label={t("recon.mismatch")} value={String(s.mismatch ?? 0)} cls="text-amber-700" />
          <Stat
            label={t("recon.missingBooks")}
            value={String(s.missing_in_books ?? 0)}
            cls="text-brand-700"
            sub={`${t("recon.itcOpportunity")}: ${inr(Number(s.itc_opportunity ?? 0))}`}
          />
          <Stat
            label={t("recon.missingPortal")}
            value={String(s.missing_in_portal ?? 0)}
            cls="text-red-700"
            sub={`${t("recon.itcAtRisk")}: ${inr(Number(s.itc_at_risk ?? 0))}`}
          />
        </div>
      )}

      {!run ? (
        <EmptyState icon={<GitCompareArrows className="h-8 w-8" />} message={t("recon.noRuns")} />
      ) : isLoading ? (
        <Spinner />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">GSTIN</th>
                <th className="px-4 py-3">{t("invoices.number")}</th>
                <th className="px-4 py-3 text-right">Tax Diff</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items?.map((it) => (
                <tr key={it.id}>
                  <td className="px-4 py-3">
                    <span className={`badge ${matchCls(it.match_status)}`}>
                      {it.match_status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{it.supplier_gstin || "—"}</td>
                  <td className="px-4 py-3 text-slate-600">{it.invoice_no || "—"}</td>
                  <td className="px-4 py-3 text-right font-medium">{inr(it.tax_diff)}</td>
                  <td className="px-4 py-3 text-right">
                    {it.resolution ? (
                      <span className="badge bg-accent-50 text-accent-700">{it.resolution}</span>
                    ) : (
                      <button
                        className="btn-secondary !px-2.5 !py-1 text-xs"
                        onClick={() =>
                          resolve.mutate({
                            itemId: it.id,
                            resolution:
                              it.match_status === "missing_in_books" ? "claimed" : "reconciled",
                          })
                        }
                      >
                        {it.match_status === "missing_in_books"
                          ? t("recon.claim")
                          : t("recon.reconcile")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function matchCls(status: string): string {
  switch (status) {
    case "matched":
      return "bg-accent-50 text-accent-700";
    case "mismatch":
      return "bg-amber-50 text-amber-700";
    case "missing_in_books":
      return "bg-brand-50 text-brand-700";
    case "missing_in_portal":
      return "bg-red-50 text-red-700";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function Stat({ label, value, cls, sub }: { label: string; value: string; cls: string; sub?: string }) {
  return (
    <div className="card">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold ${cls}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-400">{sub}</p>}
    </div>
  );
}
