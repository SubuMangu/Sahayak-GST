import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { LanguageToggle } from "@/components/LanguageToggle";
import { ErrorBox } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { Business } from "@/lib/types";
import { useAuth } from "@/store/auth";

interface GstinCheck {
  valid: boolean;
  state_name?: string | null;
}

export default function Onboarding() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { setActiveBusiness } = useAuth();

  const [legalName, setLegalName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [gstin, setGstin] = useState("");
  const [scheme, setScheme] = useState("regular");
  const [address, setAddress] = useState("");
  const [gstinCheck, setGstinCheck] = useState<GstinCheck | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Live GSTIN checksum validation as the user types.
  useEffect(() => {
    const g = gstin.trim().toUpperCase();
    if (g.length !== 15) {
      setGstinCheck(null);
      return;
    }
    let active = true;
    api
      .get<GstinCheck>(`/businesses/validate-gstin/${g}`)
      .then((r) => active && setGstinCheck(r))
      .catch(() => active && setGstinCheck({ valid: false }));
    return () => {
      active = false;
    };
  }, [gstin]);

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      const biz = await api.post<Business>("/businesses", {
        legal_name: legalName,
        trade_name: tradeName || null,
        gstin: gstin.trim().toUpperCase() || null,
        scheme,
        address: address || null,
      });
      setActiveBusiness(biz.id);
      await qc.invalidateQueries({ queryKey: ["businesses"] });
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="flex justify-end p-4">
        <LanguageToggle />
      </div>
      <div className="mx-auto max-w-lg p-4">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">{t("onboarding.title")}</h1>
        <div className="card mt-4 space-y-4">
          {error && <ErrorBox message={error} />}
          <div>
            <label className="label">{t("onboarding.legalName")}</label>
            <input className="input" value={legalName} onChange={(e) => setLegalName(e.target.value)} />
          </div>
          <div>
            <label className="label">{t("onboarding.tradeName")}</label>
            <input className="input" value={tradeName} onChange={(e) => setTradeName(e.target.value)} />
          </div>
          <div>
            <label className="label">{t("onboarding.gstin")}</label>
            <input
              className="input uppercase"
              maxLength={15}
              value={gstin}
              onChange={(e) => setGstin(e.target.value.toUpperCase())}
              placeholder="07ABCDE1234F1Z5"
            />
            {gstinCheck && (
              <p
                className={`mt-1.5 flex items-center gap-1.5 text-xs ${
                  gstinCheck.valid ? "text-accent-700" : "text-red-600"
                }`}
              >
                {gstinCheck.valid ? (
                  <>
                    <CheckCircle2 className="h-4 w-4" /> {t("onboarding.validGstin")}
                    {gstinCheck.state_name ? ` · ${gstinCheck.state_name}` : ""}
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4" /> {t("onboarding.invalidGstin")}
                  </>
                )}
              </p>
            )}
          </div>
          <div>
            <label className="label">{t("onboarding.scheme")}</label>
            <select className="input" value={scheme} onChange={(e) => setScheme(e.target.value)}>
              <option value="regular">{t("onboarding.regular")}</option>
              <option value="composition">{t("onboarding.composition")}</option>
            </select>
          </div>
          <div>
            <label className="label">{t("onboarding.address")}</label>
            <textarea className="input" rows={2} value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <button
            className="btn-primary w-full"
            disabled={!legalName || loading || (gstin.length === 15 && !gstinCheck?.valid)}
            onClick={submit}
          >
            {loading ? "…" : t("onboarding.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
