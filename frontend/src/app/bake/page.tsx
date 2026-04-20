"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useDateStore } from "@/stores/dateStore";
import AppShell from "@/components/layout/AppShell";
import EditableCell from "@/components/shared/EditableCell";
import ExportBar from "@/components/shared/ExportBar";
import { useToast } from "@/components/shared/Toast";
import type { BakePlanResponse } from "@/lib/types";

export default function BakePage() {
  const { selectedDate } = useDateStore();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading } = useQuery<BakePlanResponse>({
    queryKey: ["bake", selectedDate],
    queryFn: () => api.get(`/bake/${selectedDate}`).then((r) => r.data),
    refetchInterval: 60000,
  });

  const generate = useMutation({
    mutationFn: () => api.post(`/bake/${selectedDate}/generate`),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["bake", selectedDate] });
      if (res.data?.sync_warning) {
        toast.show(res.data.sync_warning, "error");
      } else {
        toast.show("Bake plan generated");
      }
    },
    onError: () => toast.show("Failed to generate plan", "error"),
  });

  const updateBake = useMutation({
    mutationFn: ({ flavorId, body }: { flavorId: number; body: Record<string, number | null> }) =>
      api.patch(`/bake/${selectedDate}/${flavorId}`, body),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["bake", selectedDate] });
      if (res.data?.sync_warning) {
        toast.show(res.data.sync_warning, "error");
      } else {
        toast.show("Updated");
      }
    },
    onError: () => toast.show("Failed to save", "error"),
  });

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-xl font-bold">Morning Bake Board</h2>
            <p className="text-sm text-gray-500">{selectedDate}</p>
          </div>
          <div className="flex gap-2">
            <ExportBar
              filename={`bake-plan-${selectedDate}`}
              rows={data?.rows.map((r) => ({
                code: r.flavor_code,
                flavor: r.flavor_name,
                bake: r.override_amount ?? r.amount_to_bake,
                priority: r.cooking_priority ?? "",
                website: r.website_demand,
                missing: r.missing_for_malls,
                closing_inv: r.closing_inv_yesterday,
                mall_forecast: r.mall_forecast,
                sales_trend_median: r.sales_trend_median,
                total_projection: r.total_projection,
              })) ?? []}
              labels={{
                code: "Code", flavor: "Flavor", bake: "Amount to Bake",
                priority: "Priority", website: "Website Demand",
                missing: "Missing for Malls", closing_inv: "Closing Inv Yesterday",
                mall_forecast: "Mall Forecast", sales_trend_median: "4-Week Median",
                total_projection: "Total Projection",
              }}
              keys={["code","flavor","bake","priority","website","missing","closing_inv","mall_forecast","sales_trend_median","total_projection"]}
            />
            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="bg-cookie-500 hover:bg-cookie-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 print:hidden"
            >
              {generate.isPending ? "Generating..." : "Generate Plan"}
            </button>
          </div>
        </div>

        {data && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-cyan-50 border border-cyan-200 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-cyan-700">{data.total_to_bake.toLocaleString()}</p>
              <p className="text-sm text-cyan-600">Total to Bake</p>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
              <p className="text-3xl font-bold text-gray-700">{data.total_closing_inventory.toLocaleString()}</p>
              <p className="text-sm text-gray-500">Closing Inv. Yesterday</p>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : data?.rows.length ? (
          <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-sm border-collapse min-w-[700px]">
              <thead>
                <tr className="bg-gray-100 text-left">
                  <th className="px-3 py-2 font-medium sticky left-0 bg-gray-100 z-10">Flavor</th>
                  <th className="px-3 py-2 font-medium text-center bg-green-100">Bake</th>
                  <th className="px-3 py-2 font-medium text-center">Priority</th>
                  <th className="px-3 py-2 font-medium text-center">Website</th>
                  <th className="px-3 py-2 font-medium text-center">Missing (Malls)</th>
                  <th className="px-3 py-2 font-medium text-center">Closing Inv</th>
                  <th className="px-3 py-2 font-medium text-center">Mall Forecast</th>
                  <th className="px-3 py-2 font-medium text-center">4-Wk Median</th>
                  <th className="px-3 py-2 font-medium text-center">Total Proj.</th>
                  <th className="px-3 py-2 font-medium text-center text-gray-400 text-xs">%</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.flavor_id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium sticky left-0 bg-white z-10">
                      <span className="text-xs text-gray-400 mr-1">{row.flavor_code}</span>
                      {row.flavor_name}
                    </td>
                    <EditableCell
                      value={row.override_amount ?? row.amount_to_bake}
                      highlight
                      onSave={(v) => updateBake.mutate({
                        flavorId: row.flavor_id,
                        body: { override_amount: v },
                      })}
                    />
                    <EditableCell
                      value={row.cooking_priority ?? 0}
                      onSave={(v) => updateBake.mutate({
                        flavorId: row.flavor_id,
                        body: { cooking_priority: v || null },
                      })}
                    />
                    <EditableCell
                      value={row.website_demand}
                      onSave={(v) => updateBake.mutate({
                        flavorId: row.flavor_id,
                        body: { website_demand: v },
                      })}
                    />
                    <td className="px-3 py-2 text-center">{row.missing_for_malls}</td>
                    <td className="px-3 py-2 text-center">{row.closing_inv_yesterday}</td>
                    <td className="px-3 py-2 text-center">{row.mall_forecast.toFixed(0)}</td>
                    <td className="px-3 py-2 text-center">{row.sales_trend_median.toFixed(0)}</td>
                    <td className="px-3 py-2 text-center font-medium">{row.total_projection}</td>
                    <td className="px-3 py-2 text-center text-gray-400 text-xs">
                      {(row.mall_forecast + row.sales_trend_median) > 0
                        ? `${Math.round((1 - row.total_projection / (row.mall_forecast + row.sales_trend_median)) * 100)}%`
                        : "0%"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">
            No bake plan for this date. Click &quot;Generate Plan&quot; to create one.
          </p>
        )}
      </div>
    </AppShell>
  );
}
