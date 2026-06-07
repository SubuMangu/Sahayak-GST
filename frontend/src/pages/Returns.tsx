import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { api, ApiError, downloadFile } from "@/lib/api";
import { currentPeriod, inr, periodLabel, statusBadge } from "@/lib/format";
import type { GSTRFiling } from "@/lib/types";

function periodOptions(): string[] {
  const out: string[] = [];
  const now = new Date();
  let m = now.getMonth(); // previous completed month index+1 below
  let y = now.getFullYear();
  for (let i = 0; i < 12; i++) {
    let mm = m - i;
    let yy = y;
    while (mm <= 0) {
      mm += 12;
      yy -= 1;
    }
    out.push(`${String(mm).padStart(2, "0")}${yy}`);
  }
  return out;
}

export default function Returns() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [period, setPeriod] = useState(currentPeriod());
  const [error, setError] = useState("");

  const { data: filings, isLoading } = useQuery({
    queryKey: ["filings"],
    queryFn: () => api.get<GSTRFiling[]>("/compliance/gstr"),
  });

  const generate = useMutation({
    mutationFn: (return_type: string) =>
      api.post<GSTRFiling>("/compliance/gstr/generate", { return_type, period }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["filings"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  const confirm = useMutation({
    mutationFn: (filing_id: string) =>
      api.post<GSTRFiling>("/compliance/gstr/confirm", { filing_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["filings"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  return (
    <div>
      <PageHeader title={t("returns.title")} />
      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      <div className="card mb-5">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label">{t("returns.period")}</label>
            <select className="input" value={period} onChange={(e) => setPeriod(e.target.value)}>
              {periodOptions().map((p) => (
                <option key={p} value={p}>
                  {periodLabel(p)}
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn-primary"
            onClick={() => generate.mutate("GSTR1")}
            disabled={generate.isPending}
          >
            <FileText className="h-4 w-4" /> {t("returns.generate")} {t("returns.gstr1")}
          </button>
          <button
            className="btn-primary"
            onClick={() => generate.mutate("GSTR3B")}
            disabled={generate.isPending}
          >
            <FileText className="h-4 w-4" /> {t("returns.generate")} {t("returns.gstr3b")}
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-400">{t("returns.confirmNote")}</p>
      </div>

      {isLoading ? (
        <Spinner />
      ) : !filings || filings.length === 0 ? (
        <EmptyState icon={<FileText className="h-8 w-8" />} message={t("returns.noFilings")} />
      ) : (
        <div className="space-y-3">
          {filings.map((f) => (
            <FilingCard key={f.id} filing={f} onConfirm={() => confirm.mutate(f.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

function FilingCard({ filing, onConfirm }: { filing: GSTRFiling; onConfirm: () => void }) {
  const { t } = useTranslation();
  const sb = statusBadge(filing.status);
  const s = (filing.summary ?? {}) as Record<string, unknown>;

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-800">{filing.return_type}</h3>
            <span className="text-sm text-slate-400">{periodLabel(filing.period)}</span>
            <span className={`badge ${sb.cls}`}>{sb.label}</span>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
            {filing.return_type === "GSTR1" ? (
              <>
                <span>Invoices: {String(s.total_invoices ?? 0)}</span>
                <span>Taxable: {inr(Number(s.total_taxable_value ?? 0))}</span>
                <span>Tax: {inr(Number(s.total_tax ?? 0))}</span>
              </>
            ) : (
              <>
                <span>Outward tax: {inr(Number(s.outward_tax ?? 0))}</span>
                <span>ITC: {inr(Number(s.itc_available ?? 0))}</span>
                <span>
                  Net payable:{" "}
                  {inr(Number((s.net_tax_payable as Record<string, number>)?.total ?? 0))}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="btn-secondary !px-3 !py-1.5 text-xs"
            onClick={() =>
              downloadFile(
                `/compliance/gstr/${filing.id}/export.json`,
                `${filing.return_type}_${filing.period}.json`
              )
            }
          >
            <FileJson className="h-4 w-4" /> {t("returns.exportJson")}
          </button>
          <button
            className="btn-secondary !px-3 !py-1.5 text-xs"
            onClick={() =>
              downloadFile(
                `/compliance/gstr/${filing.id}/export.xlsx`,
                `${filing.return_type}_${filing.period}.xlsx`
              )
            }
          >
            <FileSpreadsheet className="h-4 w-4" /> {t("returns.exportExcel")}
          </button>
          {filing.status === "draft" && (
            <button className="btn-accent !px-3 !py-1.5 text-xs" onClick={onConfirm}>
              <Download className="h-4 w-4" /> {t("returns.confirm")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
