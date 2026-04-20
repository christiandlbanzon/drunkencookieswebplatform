"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import AppShell from "@/components/layout/AppShell";

interface SalesSummary {
  period_days: number;
  by_location: { location: string; total: number }[];
  by_flavor: { code: string; flavor: string; total: number }[];
  by_date: { date: string; total: number }[];
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(7);

  const { data, isLoading } = useQuery<SalesSummary>({
    queryKey: ["analytics", days],
    queryFn: () => api.get(`/analytics/summary?days=${days}`).then((r) => r.data),
  });

  const grandTotal = data?.by_location.reduce((s, l) => s + l.total, 0) ?? 0;
  const maxLocQty = Math.max(...(data?.by_location.map((l) => l.total) ?? [1]));
  const maxFlavQty = Math.max(...(data?.by_flavor.map((f) => f.total) ?? [1]));
  const maxDayQty = Math.max(...(data?.by_date.map((d) => d.total) ?? [1]));

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-xl font-bold">Sales Analytics</h2>
          <div className="flex gap-1">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 rounded text-sm font-medium transition ${
                  days === d ? "bg-cookie-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : data ? (
          <>
            {/* Grand total */}
            <div className="bg-cookie-50 border border-cookie-200 rounded-xl p-4 text-center">
              <p className="text-4xl font-bold text-cookie-700">{grandTotal.toLocaleString()}</p>
              <p className="text-sm text-cookie-600">Total cookies sold ({days} days)</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* By Location */}
              <div className="bg-white rounded-xl border p-4">
                <h3 className="font-semibold mb-3">By Location</h3>
                <div className="space-y-2">
                  {data.by_location.map((loc) => (
                    <div key={loc.location} className="flex items-center gap-2">
                      <span className="text-sm w-32 truncate">{loc.location}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div
                          className="bg-cookie-400 h-full rounded-full transition-all"
                          style={{ width: `${(loc.total / maxLocQty) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-16 text-right">{loc.total.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Flavor */}
              <div className="bg-white rounded-xl border p-4">
                <h3 className="font-semibold mb-3">By Flavor</h3>
                <div className="space-y-2">
                  {data.by_flavor.map((f) => (
                    <div key={f.code} className="flex items-center gap-2">
                      <span className="text-sm w-40 truncate">
                        <span className="text-gray-400 mr-1">{f.code}</span>{f.flavor}
                      </span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                        <div
                          className="bg-cyan-400 h-full rounded-full transition-all"
                          style={{ width: `${(f.total / maxFlavQty) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-16 text-right">{f.total.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Daily trend (bar chart) */}
            <div className="bg-white rounded-xl border p-4">
              <h3 className="font-semibold mb-3">Daily Sales Trend</h3>
              <div className="flex items-end gap-1 h-40">
                {data.by_date.map((d) => (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-cookie-400 rounded-t transition-all min-h-[2px]"
                      style={{ height: `${(d.total / maxDayQty) * 100}%` }}
                      title={`${d.date}: ${d.total}`}
                    />
                    <span className="text-[9px] text-gray-400 -rotate-45 origin-top-left whitespace-nowrap">
                      {d.date.slice(5)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
