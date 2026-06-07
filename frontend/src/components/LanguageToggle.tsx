import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const toggle = () => {
    const next = i18n.language === "en" ? "hi" : "en";
    i18n.changeLanguage(next);
    localStorage.setItem("lang", next);
  };
  return (
    <button
      onClick={toggle}
      className="btn-secondary !px-3 !py-1.5 text-xs"
      aria-label="Toggle language"
    >
      <Languages className="h-4 w-4" />
      {i18n.language === "en" ? "हिंदी" : "EN"}
    </button>
  );
}
