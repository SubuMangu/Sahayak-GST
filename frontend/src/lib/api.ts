import { useAuth } from "@/store/auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const { accessToken, activeBusinessId } = useAuth.getState();
  const h: Record<string, string> = { ...extra };
  if (accessToken) h["Authorization"] = `Bearer ${accessToken}`;
  if (activeBusinessId) h["X-Business-Id"] = activeBusinessId;
  return h;
}

async function refreshTokens(): Promise<boolean> {
  const { refreshToken, setTokens, logout } = useAuth.getState();
  if (!refreshToken) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    logout();
    return false;
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  retry = true
): Promise<T> {
  const isForm = body instanceof FormData;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: authHeaders(isForm ? {} : body ? { "Content-Type": "application/json" } : {}),
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && retry) {
    if (await refreshTokens()) return request<T>(method, path, body, false);
  }

  if (!res.ok) {
    let detail = "Request failed";
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("application/json") ? res.json() : res.blob()) as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, b?: unknown) => request<T>("POST", p, b),
  patch: <T>(p: string, b?: unknown) => request<T>("PATCH", p, b),
  del: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, form: FormData) => request<T>("POST", p, form),
};

// Download a file (blob) with auth, then trigger a browser save.
export async function downloadFile(path: string, filename: string) {
  const blob = await request<Blob>("GET", path);
  const url = URL.createObjectURL(blob as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { BASE as API_BASE };
