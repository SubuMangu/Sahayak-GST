import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, Receipt, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { confidenceColor, inr, statusBadge } from "@/lib/format";
import type { InvoiceListItem } from "@/lib/types";

export default function Invoices() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);

  const [direction, setDirection] = useState<"purchase" | "sales">("purchase");
  const [filter, setFilter] = useState<string>(params.get("status_filter") || "");
  const [error, setError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["invoices", filter],
    queryFn: () =>
      api.get<InvoiceListItem[]>(`/invoices${filter ? `?status_filter=${filter}` : ""}`),
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("direction", direction);
      return api.upload<{ id: string }>("/invoices/upload", form);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/invoices/${res.id}`);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  const bulkApprove = useMutation({
    mutationFn: () => api.post<{ approved: number }>("/invoices/bulk-approve", {
      confidence_threshold: 0.85,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const onFile = (f?: File | null) => {
    if (f) {
      setError("");
      upload.mutate(f);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("invoices.title")}
        action={
          <div className="flex gap-2">
            <button
              className="btn-secondary"
              onClick={() => bulkApprove.mutate()}
              disabled={bulkApprove.isPending}
            >
              <CheckCheck className="h-4 w-4" /> {t("review.bulkApprove")}
            </button>
            <button className="btn-primary" onClick={() => fileRef.current?.click()}>
              <Upload className="h-4 w-4" /> {t("invoices.upload")}
            </button>
          </div>
        }
      />

      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      {/* Upload drop zone */}
      <div
        className="mb-5 cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 bg-white p-6 text-center hover:border-brand-400"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          onFile(e.dataTransfer.files?.[0]);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,image/*"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <Upload className="mx-auto mb-2 h-7 w-7 text-slate-400" />
        <p className="text-sm text-slate-500">
          {upload.isPending ? t("invoices.uploading") : t("invoices.dropHere")}
        </p>
        <div className="mt-3 inline-flex items-center gap-2 text-sm">
          <span className="text-slate-400">{t("invoices.direction")}:</span>
          <select
            className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
            value={direction}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => setDirection(e.target.value as "purchase" | "sales")}
          >
            <option value="purchase">{t("invoices.purchase")}</option>
            <option value="sales">{t("invoices.sales")}</option>
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ["", "all"],
          ["needs_review", "needsReview"],
          ["confirmed", "confirmed"],
        ].map(([val, key]) => (
          <button
            key={key}
            onClick={() => setFilter(val)}
            className={`badge px-3 py-1.5 ${
              filter === val ? "bg-brand-700 text-white" : "bg-white text-slate-600 border border-slate-200"
            }`}
          >
            {t(`invoices.${key}`)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data || data.length === 0 ? (
        <EmptyState icon={<Receipt className="h-8 w-8" />} message={t("invoices.noInvoices")} />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">{t("invoices.party")}</th>
                <th className="px-4 py-3">{t("invoices.number")}</th>
                <th className="hidden px-4 py-3 sm:table-cell">{t("invoices.date")}</th>
                <th className="px-4 py-3 text-right">{t("invoices.total")}</th>
                <th className="px-4 py-3">{t("invoices.status")}</th>
                <th className="hidden px-4 py-3 md:table-cell">{t("invoices.confidence")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((inv) => {
                const sb = statusBadge(inv.status);
                return (
                  <tr
                    key={inv.id}
                    className="cursor-pointer hover:bg-slate-50"
                    onClick={() => navigate(`/invoices/${inv.id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {inv.counterparty_name || "—"}
                      <span className="ml-2 text-xs text-slate-400">{inv.direction}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{inv.invoice_no || "—"}</td>
                    <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">
                      {inv.invoice_date || "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{inr(inv.total_value)}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${sb.cls}`}>{sb.label}</span>
                    </td>
                    <td className="hidden px-4 py-3 md:table-cell">
                      <span className={`badge ${confidenceColor(inv.overall_confidence)}`}>
                        {Math.round(inv.overall_confidence * 100)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
