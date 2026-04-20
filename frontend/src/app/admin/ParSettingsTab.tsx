"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { useToast } from "@/components/shared/Toast";

interface Location {
  id: number;
  name: string;
  display_name: string;
}

interface ParSetting {
  location_id: number;
  effective_date: string;
  reduction_pct: number;
  minimum_par: number;
  median_weeks: number;
}

export default function ParSettingsTab() {
  const qc = useQueryClient();
  const toast = useToast();
  const [selectedLoc, setSelectedLoc] = useState<number | null>(null);

  const { data: locations } = useQuery<Location[]>({
    queryKey: ["admin-locations"],
    queryFn: () => api.get("/admin/locations").then((r) => r.data),
  });

  const { data: settings } = useQuery<ParSetting[]>({
    queryKey: ["par-settings", selectedLoc],
    queryFn: () => selectedLoc ? api.get(`/admin/par-settings/${selectedLoc}`).then((r) => r.data) : Promise.resolve([]),
    enabled: !!selectedLoc,
  });

  const upsert = useMutation({
    mutationFn: ({ loc, date, body }: any) => api.put(`/admin/par-settings/${loc}/${date}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["par-settings", selectedLoc] });
      toast.show("PAR settings saved");
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ reduction_pct: 0, minimum_par: 10, median_weeks: 4 });

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        PAR settings control how each location computes its PAR values.
        Reduction % trims the median (e.g., -20% keeps extra safety stock,
        +15% reduces by 15%). Minimum PAR is the floor. Median Weeks is how
        far back to average.
      </p>

      <div className="flex gap-2 flex-wrap">
        {locations?.map((loc) => (
          <button
            key={loc.id}
            onClick={() => setSelectedLoc(loc.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              selectedLoc === loc.id
                ? "bg-cookie-500 text-white"
                : "bg-white border hover:bg-gray-50"
            }`}
          >
            {loc.display_name}
          </button>
        ))}
      </div>

      {selectedLoc && (
        <>
          <div className="bg-white rounded-xl border p-4 space-y-3">
            <h4 className="font-semibold text-sm">Set New PAR Settings</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="text-sm">
                Reduction %
                <input
                  type="number"
                  step="0.01"
                  value={form.reduction_pct}
                  onChange={(e) => setForm({ ...form, reduction_pct: parseFloat(e.target.value) || 0 })}
                  className="block w-full border rounded-lg px-3 py-2 text-sm mt-1"
                />
                <span className="text-xs text-gray-400">e.g. 0.15 = 15% reduction, -0.2 = 20% increase</span>
              </label>
              <label className="text-sm">
                Minimum PAR
                <input
                  type="number"
                  value={form.minimum_par}
                  onChange={(e) => setForm({ ...form, minimum_par: parseInt(e.target.value) || 10 })}
                  className="block w-full border rounded-lg px-3 py-2 text-sm mt-1"
                />
              </label>
              <label className="text-sm">
                Median Weeks
                <input
                  type="number"
                  value={form.median_weeks}
                  onChange={(e) => setForm({ ...form, median_weeks: parseInt(e.target.value) || 4 })}
                  className="block w-full border rounded-lg px-3 py-2 text-sm mt-1"
                />
              </label>
            </div>
            <button
              onClick={() => upsert.mutate({ loc: selectedLoc, date: today, body: form })}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              Apply (effective today)
            </button>
          </div>

          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b text-left">
                  <th className="px-4 py-2">Effective Date</th>
                  <th className="px-4 py-2">Reduction %</th>
                  <th className="px-4 py-2">Min PAR</th>
                  <th className="px-4 py-2">Median Weeks</th>
                </tr>
              </thead>
              <tbody>
                {settings?.length ? settings.map((s) => (
                  <tr key={s.effective_date} className="border-b">
                    <td className="px-4 py-2">{s.effective_date}</td>
                    <td className="px-4 py-2">{(s.reduction_pct * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2">{s.minimum_par}</td>
                    <td className="px-4 py-2">{s.median_weeks}</td>
                  </tr>
                )) : (
                  <tr><td colSpan={4} className="px-4 py-4 text-center text-gray-400">No PAR settings yet — using defaults (0%, min 10, 4 weeks)</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
