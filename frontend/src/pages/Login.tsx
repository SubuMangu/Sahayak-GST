import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { LanguageToggle } from "@/components/LanguageToggle";
import { ErrorBox } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/store/auth";

interface OtpResp {
  message: string;
  dev_otp?: string | null;
}
interface TokenResp {
  access_token: string;
  refresh_token: string;
  onboarding_complete: boolean;
}

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setTokens } = useAuth();

  const [step, setStep] = useState<"mobile" | "otp">("mobile");
  const [mobile, setMobile] = useState("");
  const [code, setCode] = useState("");
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const sendOtp = async () => {
    setError("");
    setLoading(true);
    try {
      const r = await api.post<OtpResp>("/auth/request-otp", { mobile });
      setDevOtp(r.dev_otp ?? null);
      if (r.dev_otp) setCode(r.dev_otp);
      setStep("otp");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const verify = async () => {
    setError("");
    setLoading(true);
    try {
      const r = await api.post<TokenResp>("/auth/verify-otp", { mobile, code });
      setTokens(r.access_token, r.refresh_token);
      navigate(r.onboarding_complete ? "/" : "/onboarding");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-brand-50 to-accent-50">
      <div className="flex justify-end p-4">
        <LanguageToggle />
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="mb-6 flex flex-col items-center text-center">
            <img src="/favicon.svg" alt="" className="h-14 w-14" />
            <h1 className="mt-3 text-2xl font-bold text-brand-900">{t("app.name")}</h1>
            <p className="text-sm text-slate-500">{t("app.tagline")}</p>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold">{t("login.title")}</h2>
            <p className="mt-1 text-sm text-slate-500">{t("login.subtitle")}</p>

            {error && <div className="mt-4"><ErrorBox message={error} /></div>}

            {step === "mobile" ? (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="label" htmlFor="mobile">{t("login.mobile")}</label>
                  <div className="flex items-center gap-2">
                    <span className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-500">
                      +91
                    </span>
                    <input
                      id="mobile"
                      className="input"
                      inputMode="numeric"
                      maxLength={10}
                      placeholder="98XXXXXXXX"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value.replace(/\D/g, ""))}
                    />
                  </div>
                </div>
                <button
                  className="btn-primary w-full"
                  disabled={mobile.length !== 10 || loading}
                  onClick={sendOtp}
                >
                  {loading ? "…" : t("login.sendOtp")}
                </button>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="label" htmlFor="otp">{t("login.enterOtp")}</label>
                  <input
                    id="otp"
                    className="input tracking-[0.5em] text-center text-lg"
                    inputMode="numeric"
                    maxLength={6}
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  />
                  {devOtp && (
                    <p className="mt-2 text-xs text-accent-700">
                      {t("login.devOtp")}: <b>{devOtp}</b>
                    </p>
                  )}
                </div>
                <button
                  className="btn-primary w-full"
                  disabled={code.length !== 6 || loading}
                  onClick={verify}
                >
                  {loading ? "…" : t("login.verify")}
                </button>
                <button className="btn-secondary w-full" onClick={sendOtp} disabled={loading}>
                  {t("login.resend")}
                </button>
              </div>
            )}
          </div>

          <p className="mt-4 px-2 text-center text-xs text-slate-400">{t("login.disclaimer")}</p>
        </div>
      </div>
    </div>
  );
}
