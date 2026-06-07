import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  activeBusinessId: string | null;
  setTokens: (access: string, refresh: string) => void;
  setActiveBusiness: (id: string | null) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      activeBusinessId: null,
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setActiveBusiness: (id) => set({ activeBusinessId: id }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, activeBusinessId: null }),
    }),
    { name: "sahayak-auth" }
  )
);
