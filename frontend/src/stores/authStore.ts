import { create } from "zustand";
import type { LoginResponse } from "@/lib/types";

interface AuthState {
  token: string | null;
  role: string | null;
  displayName: string | null;
  locationId: number | null;
  setAuth: (data: LoginResponse) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  role: null,
  displayName: null,
  locationId: null,

  setAuth: (data) => {
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("role", data.role);
    localStorage.setItem("displayName", data.display_name);
    if (data.location_id) localStorage.setItem("locationId", String(data.location_id));
    set({
      token: data.access_token,
      role: data.role,
      displayName: data.display_name,
      locationId: data.location_id,
    });
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("displayName");
    localStorage.removeItem("locationId");
    set({ token: null, role: null, displayName: null, locationId: null });
  },

  hydrate: () => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const displayName = localStorage.getItem("displayName");
    const locationId = localStorage.getItem("locationId");
    if (token && role) {
      set({
        token,
        role,
        displayName,
        locationId: locationId ? Number(locationId) : null,
      });
    }
  },
}));
