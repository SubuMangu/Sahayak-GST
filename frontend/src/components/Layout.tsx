import {
  BarChart3,
  Bell,
  FileText,
  GitCompareArrows,
  LayoutDashboard,
  LogOut,
  Receipt,
  Settings as SettingsIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Business, AppNotification } from "@/lib/types";
import { useAuth } from "@/store/auth";
import { LanguageToggle } from "./LanguageToggle";

const navItems = [
  { to: "/", icon: LayoutDashboard, key: "dashboard", end: true },
  { to: "/invoices", icon: Receipt, key: "invoices" },
  { to: "/returns", icon: FileText, key: "returns" },
  { to: "/reconciliation", icon: GitCompareArrows, key: "reconciliation" },
  { to: "/billing", icon: BarChart3, key: "billing" },
  { to: "/settings", icon: SettingsIcon, key: "settings" },
];

export default function Layout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { logout, activeBusinessId, setActiveBusiness } = useAuth();

  const { data: businesses } = useQuery({
    queryKey: ["businesses"],
    queryFn: () => api.get<Business[]>("/businesses"),
  });
  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => api.get<AppNotification[]>("/notifications?unread_only=true"),
    enabled: !!activeBusinessId,
  });

  const unread = notifications?.length ?? 0;

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Sidebar (desktop) */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <Brand />
        <BusinessSwitcher
          businesses={businesses ?? []}
          activeId={activeBusinessId}
          onChange={setActiveBusiness}
        />
        <nav className="mt-4 flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <item.icon className="h-5 w-5" />
              {t(`nav.${item.key}`)}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          <LogOut className="h-5 w-5" /> {t("nav.logout")}
        </button>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <Brand />
          <LanguageToggle />
        </header>

        <div className="hidden items-center justify-end gap-3 border-b border-slate-200 bg-white px-6 py-3 md:flex">
          <button
            className="relative rounded-full p-2 text-slate-500 hover:bg-slate-100"
            onClick={() => navigate("/notifications")}
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>
          <LanguageToggle />
        </div>

        <main className="flex-1 p-4 pb-24 md:p-6">
          <Outlet />
        </main>

        {/* Bottom nav (mobile, large tap targets — FR-012 accessibility) */}
        <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-slate-200 bg-white py-1.5 md:hidden">
          {navItems.slice(0, 5).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 text-[10px] font-medium ${
                  isActive ? "text-brand-700" : "text-slate-500"
                }`
              }
            >
              <item.icon className="h-5 w-5" />
              {t(`nav.${item.key}`)}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}

function Brand() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className="text-lg font-bold text-brand-900">{t("app.name")}</span>
    </div>
  );
}

function BusinessSwitcher({
  businesses,
  activeId,
  onChange,
}: {
  businesses: Business[];
  activeId: string | null;
  onChange: (id: string) => void;
}) {
  if (businesses.length === 0) return null;
  return (
    <select
      className="input mt-4"
      value={activeId ?? businesses[0]?.id}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Switch business"
    >
      {businesses.map((b) => (
        <option key={b.id} value={b.id}>
          {b.trade_name || b.legal_name}
        </option>
      ))}
    </select>
  );
}
