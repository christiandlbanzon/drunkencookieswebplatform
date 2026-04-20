"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import AppShell from "@/components/layout/AppShell";

interface LocationOps {
  location_id: number;
  location_name: string;
  live_sales: number;
  opening_stock: number;
  dispatched: number;
  sell_through_pct: number;
  pending_2nd_delivery: number;
  low_stock_flavors: { flavor: string; remaining: number }[];
  status: string;
}

interface LiveOpsData {
  date: string;
  locations: LocationOps[];
}

export default function OpsPage() {
  const { data, isLoading } = useQuery<LiveOpsData>({
    queryKey: ["live-ops"],
    queryFn: () => api.get("/analytics/live-ops").then((r) => r.data),
    refetchInterval: 30000, // refresh every 30 seconds
  });

  const totalSales = data?.locations.reduce((s, l) => s + l.live_sales, 0) ?? 0;
  const totalDispatched = data?.locations.reduce((s, l) => s + l.dispatched, 0) ?? 0;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">Live Operations Center</h2>
            <p className="text-sm text-gray-500">{data?.date} — refreshes every 30s</p>
          </div>
          <div className="flex gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-cookie-600">{totalSales.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Live Sales</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-600">{totalDispatched.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Dispatched</p>
            </div>
          </div>
        </div>

        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data?.locations.map((loc) => (
              <div
                key={loc.location_id}
                className={`rounded-xl border-2 p-4 transition ${
                  loc.status === "alert"
                    ? "border-red-300 bg-red-50"
                    : "border-gray-200 bg-white"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-lg">{loc.location_name}</h3>
                  {loc.pending_2nd_delivery > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full animate-pulse">
                      2nd Delivery Requested
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="text-center">
                    <p className="text-xl font-bold text-green-600">{loc.live_sales}</p>
                    <p className="text-xs text-gray-500">Sold Today</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-gray-600">{loc.opening_stock}</p>
                    <p className="text-xs text-gray-500">Opening</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-blue-600">{loc.dispatched}</p>
                    <p className="text-xs text-gray-500">Dispatched</p>
                  </div>
                </div>

                {/* Sell-through bar */}
                <div className="mb-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">Sell-through</span>
                    <span className={`font-medium ${
                      loc.sell_through_pct > 80 ? "text-red-600" :
                      loc.sell_through_pct > 50 ? "text-yellow-600" : "text-green-600"
                    }`}>{loc.sell_through_pct}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        loc.sell_through_pct > 80 ? "bg-red-500" :
                        loc.sell_through_pct > 50 ? "bg-yellow-500" : "bg-green-500"
                      }`}
                      style={{ width: `${Math.min(loc.sell_through_pct, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Low stock warnings */}
                {loc.low_stock_flavors.length > 0 && (
                  <div className="mt-2 pt-2 border-t">
                    <p className="text-xs text-red-600 font-medium mb-1">Low Stock:</p>
                    <div className="flex flex-wrap gap-1">
                      {loc.low_stock_flavors.map((f) => (
                        <span
                          key={f.flavor}
                          className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded"
                        >
                          {f.flavor} ({f.remaining})
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
