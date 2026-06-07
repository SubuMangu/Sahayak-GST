import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { Business } from "@/lib/types";

interface Me {
  full_name?: string | null;
  email?: string | null;
  mobile: string;
  preferred_language: string;
}

export default function Settings() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();

  const { data: me, isLoading } = useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/auth/me") });
  const { data: biz } = useQuery({
    queryKey: ["current-business"],
    queryFn: () => api.get<Business>("/businesses/current"),
  });

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (me) {
      setName(me.full_name ?? "");
      setEmail(me.email ?? "");
    }
  }, [me]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<Me>(
        `/auth/me?full_name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&preferred_language=${i18n.language}`
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });

  if (isLoading || !me) return <Spinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader title={t("settings.title")} />

      <div className="card mb-4 space-y-3">
        <h3 className="font-semibold text-slate-800">{t("settings.profile")}</h3>
        <div>
          <label className="label">{t("settings.name")}</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label">{t("settings.email")}</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label">{t("login.mobile")}</label>
          <input className="input bg-slate-50" value={`+91 ${me.mobile}`} readOnly />
        </div>
        <div>
          <label className="label">{t("settings.language")}</label>
          <select
            className="input"
            value={i18n.language}
            onChange={(e) => {
              i18n.changeLanguage(e.target.value);
              localStorage.setItem("lang", e.target.value);
            }}
          >
            <option value="en">English</option>
            <option value="hi">हिंदी</option>
          </select>
        </div>
        <button className="btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "…" : t("settings.save")}
        </button>
      </div>

      {biz && (
        <div className="card mb-4">
          <h3 className="mb-2 font-semibold text-slate-800">{t("settings.business")}</h3>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-slate-500">{t("onboarding.legalName")}</dt>
            <dd className="font-medium">{biz.legal_name}</dd>
            <dt className="text-slate-500">{t("onboarding.gstin")}</dt>
            <dd className="font-medium">{biz.gstin || "—"}</dd>
            <dt className="text-slate-500">{t("onboarding.scheme")}</dt>
            <dd className="font-medium capitalize">{biz.scheme}</dd>
          </dl>
        </div>
      )}

      <div className="card border-slate-200">
        <h3 className="mb-2 flex items-center gap-2 font-semibold text-slate-800">
          <ShieldCheck className="h-4 w-4 text-accent-600" /> {t("settings.dataPrivacy")}
        </h3>
        <p className="mb-3 text-sm text-slate-500">{t("settings.dpdpNote")}</p>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary">
            <Download className="h-4 w-4" /> {t("settings.exportData")}
          </button>
          <button className="btn-secondary !text-red-600">
            <Trash2 className="h-4 w-4" /> {t("settings.deleteAccount")}
          </button>
        </div>
      </div>
    </div>
  );
}
