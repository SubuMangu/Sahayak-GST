import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, CheckCircle2, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { ErrorBox, Spinner } from "@/components/ui";
import { api, API_BASE, ApiError } from "@/lib/api";
import { inr } from "@/lib/format";
import type { InvoiceDetail, LineItem } from "@/lib/types";
import { useAuth } from "@/store/auth";

export default function InvoiceReview() {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { accessToken, activeBusinessId } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api.get<InvoiceDetail>(`/invoices/${id}`),
  });

  const [form, setForm] = useState<Partial<InvoiceDetail>>({});
  const [items, setItems] = useState<LineItem[]>([]);
  const [error, setError] = useState("");
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm(data);
      setItems(data.line_items ?? []);
    }
  }, [data]);

  // Load the original document (auth-protected) as an object URL.
  useEffect(() => {
    if (!id || !data?.file_name) return;
    let url: string | null = null;
    fetch(`${API_BASE}/invoices/${id}/file`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(activeBusinessId ? { "X-Business-Id": activeBusinessId } : {}),
      },
    })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => {
        if (b) {
          url = URL.createObjectURL(b);
          setFileUrl(url);
        }
      });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [id, data?.file_name, accessToken, activeBusinessId]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<InvoiceDetail>(`/invoices/${id}`, {
        counterparty_name: form.counterparty_name,
        counterparty_gstin: form.counterparty_gstin,
        invoice_no: form.invoice_no,
        invoice_date: form.invoice_date,
        place_of_supply: form.place_of_supply,
        line_items: items,
      }),
    onSuccess: (res) => {
      qc.setQueryData(["invoice", id], res);
      qc.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  const confirm = useMutation({
    mutationFn: () => api.post<InvoiceDetail>(`/invoices/${id}/confirm`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["invoices"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate("/invoices");
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : t("common.error")),
  });

  if (isLoading || !data) return <Spinner />;

  const setItem = (i: number, key: keyof LineItem, value: string) => {
    setItems((prev) =>
      prev.map((it, idx) =>
        idx === i
          ? { ...it, [key]: key === "description" || key === "hsn" ? value : Number(value) }
          : it
      )
    );
  };

  const conf = (field: string) => data.confidence?.[field] ?? 1;
  const confClass = (field: string) => {
    const c = conf(field);
    return c >= 0.85 ? "" : c >= 0.6 ? "border-amber-400" : "border-red-400";
  };

  return (
    <div>
      <button className="btn-secondary mb-4" onClick={() => navigate(-1)}>
        <ArrowLeft className="h-4 w-4" /> {t("common.back")}
      </button>

      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Original document */}
        <div className="card">
          <h3 className="mb-3 font-semibold text-slate-800">{t("review.original")}</h3>
          {fileUrl ? (
            data.file_mime?.includes("pdf") ? (
              <iframe src={fileUrl} title="invoice" className="h-[70vh] w-full rounded-lg border" />
            ) : (
              <img src={fileUrl} alt="invoice" className="max-h-[70vh] w-full rounded-lg object-contain" />
            )
          ) : (
            <div className="flex h-64 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">
              {data.file_name || "—"}
            </div>
          )}
        </div>

        {/* Extracted form */}
        <div className="space-y-4">
          {/* Anomalies */}
          {(data.anomalies?.length ?? 0) > 0 && (
            <div className="card border-amber-200 bg-amber-50">
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-amber-800">
                <AlertTriangle className="h-4 w-4" /> {t("review.anomalies")}
              </h3>
              <ul className="space-y-1 text-sm text-amber-800">
                {data.anomalies!.map((a, i) => (
                  <li key={i} className="flex gap-2">
                    <span
                      className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${
                        a.severity === "high"
                          ? "bg-red-500"
                          : a.severity === "medium"
                            ? "bg-amber-500"
                            : "bg-slate-400"
                      }`}
                    />
                    {a.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="card space-y-3">
            <h3 className="font-semibold text-slate-800">{t("review.extracted")}</h3>
            <Field label={t("invoices.party")}>
              <input
                className={`input ${confClass("counterparty_name")}`}
                value={form.counterparty_name ?? ""}
                onChange={(e) => setForm({ ...form, counterparty_name: e.target.value })}
              />
            </Field>
            <Field label={t("onboarding.gstin")}>
              <input
                className={`input uppercase ${confClass("counterparty_gstin")}`}
                value={form.counterparty_gstin ?? ""}
                onChange={(e) => setForm({ ...form, counterparty_gstin: e.target.value.toUpperCase() })}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("invoices.number")}>
                <input
                  className={`input ${confClass("invoice_no")}`}
                  value={form.invoice_no ?? ""}
                  onChange={(e) => setForm({ ...form, invoice_no: e.target.value })}
                />
              </Field>
              <Field label={t("invoices.date")}>
                <input
                  type="date"
                  className={`input ${confClass("invoice_date")}`}
                  value={form.invoice_date ?? ""}
                  onChange={(e) => setForm({ ...form, invoice_date: e.target.value })}
                />
              </Field>
            </div>
          </div>

          {/* Line items */}
          <div className="card">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">{t("review.lineItems")}</h3>
              <button
                className="btn-secondary !px-2 !py-1 text-xs"
                onClick={() =>
                  setItems([...items, { description: "", hsn: "", taxable_value: 0, gst_rate: 18 }])
                }
              >
                <Plus className="h-3.5 w-3.5" /> {t("review.addItem")}
              </button>
            </div>
            <div className="space-y-2">
              {items.map((it, i) => (
                <div key={i} className="grid grid-cols-12 gap-1.5">
                  <input
                    className="input col-span-4 !px-2 !py-1.5 text-xs"
                    placeholder={t("review.description")}
                    value={it.description ?? ""}
                    onChange={(e) => setItem(i, "description", e.target.value)}
                  />
                  <input
                    className="input col-span-2 !px-2 !py-1.5 text-xs"
                    placeholder={t("review.hsn")}
                    value={it.hsn ?? ""}
                    onChange={(e) => setItem(i, "hsn", e.target.value)}
                  />
                  <input
                    className="input col-span-3 !px-2 !py-1.5 text-xs"
                    type="number"
                    placeholder={t("invoices.taxable")}
                    value={it.taxable_value}
                    onChange={(e) => setItem(i, "taxable_value", e.target.value)}
                  />
                  <input
                    className="input col-span-2 !px-2 !py-1.5 text-xs"
                    type="number"
                    placeholder="%"
                    value={it.gst_rate}
                    onChange={(e) => setItem(i, "gst_rate", e.target.value)}
                  />
                  <button
                    className="col-span-1 flex items-center justify-center text-slate-400 hover:text-red-500"
                    onClick={() => setItems(items.filter((_, idx) => idx !== i))}
                    aria-label="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
              <Row label="Taxable" value={inr(data.taxable_value)} />
              <Row label="CGST" value={inr(data.cgst)} />
              <Row label="SGST" value={inr(data.sgst)} />
              <Row label="IGST" value={inr(data.igst)} />
              <Row label="Total" value={inr(data.total_value)} bold />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              className="btn-secondary flex-1"
              onClick={() => save.mutate()}
              disabled={save.isPending}
            >
              {save.isPending ? "…" : t("review.save")}
            </button>
            <button
              className="btn-accent flex-1"
              onClick={() => confirm.mutate()}
              disabled={confirm.isPending || data.status === "confirmed"}
            >
              <CheckCircle2 className="h-4 w-4" />
              {data.status === "confirmed" ? t("invoices.confirmed") : t("review.confirm")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? "font-bold text-slate-900" : "text-slate-600"}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
