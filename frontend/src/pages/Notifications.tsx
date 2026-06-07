import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellOff } from "lucide-react";
import { useTranslation } from "react-i18next";

import { EmptyState, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { AppNotification } from "@/lib/types";

export default function Notifications() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notifications", "all"],
    queryFn: () => api.get<AppNotification[]>("/notifications"),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAll = useMutation({
    mutationFn: () => api.post("/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  if (isLoading) return <Spinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader
        title={t("nav.dashboard") === "Dashboard" ? "Notifications" : "सूचनाएं"}
        action={
          <button className="btn-secondary" onClick={() => markAll.mutate()}>
            <BellOff className="h-4 w-4" /> Read all
          </button>
        }
      />
      {!data || data.length === 0 ? (
        <EmptyState icon={<Bell className="h-8 w-8" />} message="No notifications yet." />
      ) : (
        <div className="space-y-2">
          {data.map((n) => (
            <button
              key={n.id}
              onClick={() => markRead.mutate(n.id)}
              className={`card flex w-full items-start gap-3 text-left ${
                n.is_read ? "opacity-60" : ""
              }`}
            >
              <Bell className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
              <div>
                <p className="font-medium text-slate-800">{n.title}</p>
                <p className="text-sm text-slate-500">{n.body}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              {!n.is_read && <span className="ml-auto h-2 w-2 rounded-full bg-brand-600" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
