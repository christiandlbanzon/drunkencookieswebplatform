"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import AppShell from "@/components/layout/AppShell";
import type { Location } from "@/lib/types";

export default function StoreIndexPage() {
  const router = useRouter();
  const { role, locationId, hydrate } = useAuthStore();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    hydrate();
    setReady(true);
  }, [hydrate]);

  useEffect(() => {
    if (ready && role === "store_manager" && locationId) {
      router.replace(`/store/${locationId}`);
    }
  }, [ready, role, locationId, router]);

  const { data: locations } = useQuery<Location[]>({
    queryKey: ["locations"],
    queryFn: () => api.get("/admin/locations").then((r) => r.data),
    enabled: ready && role !== "store_manager",
  });

  if (!ready) return null;

  if (role === "store_manager") {
    return (
      <AppShell>
        <p className="text-gray-400 text-center py-8">Redirecting...</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Select Location</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {locations?.map((loc) => (
            <button
              key={loc.id}
              onClick={() => router.push(`/store/${loc.id}`)}
              className="bg-white border rounded-xl p-6 text-left hover:border-cookie-400 hover:shadow-md transition"
            >
              <p className="font-semibold text-lg">{loc.display_name}</p>
              <p className="text-sm text-gray-500">View inventory</p>
            </button>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
