"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useDateStore } from "@/stores/dateStore";
import AppShell from "@/components/layout/AppShell";
import EditableCell from "@/components/shared/EditableCell";
import ExportBar from "@/components/shared/ExportBar";
import { useToast } from "@/components/shared/Toast";
import type { DispatchPlanResponse, DispatchRow } from "@/lib/types";

export default function DispatchPage() {
  const { selectedDate } = useDateStore();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading } = useQuery<DispatchPlanResponse>({
    queryKey: ["dispatch", selectedDate],
    queryFn: () => api.get(`/dispatch/${selectedDate}`).then((r) => r.data),
    refetchInterval: 60000,
  });

  const { data: websiteOrders } = useQuery<{
    midnight_6pm: Record<string, number>;
    "6pm_midnight": Record<string, number>;
    total_orders?: number;
  }>({
    queryKey: ["website-orders", selectedDate],
    queryFn: () => api.get(`/sales/website-orders/${selectedDate}`).then((r) => r.data),
  });

  const generate = useMutation({
    mutationFn: () => api.post(`/dispatch/${selectedDate}/generate`),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["dispatch", selectedDate] });
      if (res.data?.sync_warning) {
        toast.show(res.data.sync_warning, "error");
      } else {
        toast.show("Dispatch plan generated");
      }
    },
    onError: () => toast.show("Failed to generate plan", "error"),
  });

  const updateDispatch = useMutation({
    mutationFn: ({ locationId, flavorId, amount }: { locationId: number; flavorId: number; amount: number | null }) =>
      api.patch(`/dispatch/${selectedDate}/${locationId}/${flavorId}`, { override_amount: amount }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["dispatch", selectedDate] });
      if (res.data?.sync_warning) {
        toast.show(res.data.sync_warning, "error");
      } else {
        toast.show("Updated");
      }
    },
    onError: () => toast.show("Failed to save", "error"),
  });

  const grandTotal = data?.locations.reduce((sum, loc) => sum + loc.total_to_send, 0) ?? 0;

  // Build bake summary: per flavor, sum "Send" across all locations + website orders
  const bakeSummary = buildBakeSummary(data, websiteOrders);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-xl font-bold">Dispatch Board</h2>
            <p className="text-sm text-gray-500">
              {selectedDate}
              {data && <span className="ml-2 font-medium text-cookie-600">({grandTotal.toLocaleString()} total)</span>}
            </p>
          </div>
          <div className="flex gap-2">
            <ExportBar
              filename={`dispatch-plan-${selectedDate}`}
              rows={data?.locations.flatMap((loc) => loc.rows.map((r) => ({
                location: loc.location_name,
                code: r.flavor_code,
                flavor: r.flavor_name,
                median: r.sales_trend_median,
                par: r.par_value,
                adjusted_par: r.adjusted_par,
                inventory: r.live_inventory,
                amount_to_send: r.override_amount ?? r.amount_to_send,
                status: r.dispatch_status,
              }))) ?? []}
              labels={{
                location: "Location", code: "Code", flavor: "Flavor",
                median: "4-Week Median", par: "PAR", adjusted_par: "Adjusted PAR",
                inventory: "Inventory", amount_to_send: "Amount to Send", status: "Status",
              }}
              keys={["location","code","flavor","median","par","adjusted_par","inventory","amount_to_send","status"]}
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

        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : data?.locations.length ? (
          <>
            {/* Per-location dispatch blocks */}
            {data.locations.map((loc) => (
              <div key={loc.location_id} className="bg-white rounded-xl border shadow-sm overflow-hidden break-inside-avoid">
                <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b gap-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{loc.location_name}</h3>
                    {loc.dispatch_status !== "pending" && (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        loc.dispatch_status === "packed" ? "bg-blue-100 text-blue-700" :
                        loc.dispatch_status === "sent" ? "bg-green-100 text-green-700" :
                        loc.dispatch_status === "received" ? "bg-gray-100 text-gray-600" :
                        ""
                      }`}>{loc.dispatch_status}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-cookie-600">
                      {loc.total_to_send.toLocaleString()}
                    </span>
                    {loc.dispatch_status === "pending" && (
                      <button
                        onClick={() => api.patch(`/dispatch/${selectedDate}/${loc.location_id}/confirm?new_status=packed`).then(() => { queryClient.invalidateQueries({ queryKey: ["dispatch"] }); toast.show(`${loc.location_name} marked packed`); })}
                        className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 print:hidden"
                      >Packed</button>
                    )}
                    {loc.dispatch_status === "packed" && (
                      <button
                        onClick={() => api.patch(`/dispatch/${selectedDate}/${loc.location_id}/confirm?new_status=sent`).then(() => { queryClient.invalidateQueries({ queryKey: ["dispatch"] }); toast.show(`${loc.location_name} marked sent`); })}
                        className="text-xs bg-green-500 text-white px-2 py-1 rounded hover:bg-green-600 print:hidden"
                      >Sent</button>
                    )}
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[500px]">
                    <thead>
                      <tr className="text-left text-gray-500 border-b">
                        <th className="px-3 py-2 sticky left-0 bg-white z-10">Flavor</th>
                        <th className="px-3 py-2 text-center">4-Wk Median</th>
                        <th className="px-3 py-2 text-center">PAR</th>
                        <th className="px-3 py-2 text-center">Adj. PAR</th>
                        <th className="px-3 py-2 text-center">Inventory</th>
                        <th className="px-3 py-2 text-center bg-green-100 font-semibold">Send</th>
                        <th className="px-3 py-2 text-center text-gray-400 text-xs">%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loc.rows.map((row) => (
                        <tr key={row.flavor_id} className="border-b hover:bg-gray-50">
                          <td className="px-3 py-1.5 sticky left-0 bg-white z-10">
                            <span className="text-xs text-gray-400 mr-1">{row.flavor_code}</span>
                            {row.flavor_name}
                          </td>
                          <td className="px-3 py-1.5 text-center">{row.sales_trend_median.toFixed(0)}</td>
                          <td className="px-3 py-1.5 text-center">{row.par_value.toFixed(0)}</td>
                          <td className="px-3 py-1.5 text-center">{row.adjusted_par}</td>
                          <td className="px-3 py-1.5 text-center">{row.live_inventory}</td>
                          <EditableCell
                            value={row.override_amount ?? row.amount_to_send}
                            highlight
                            onSave={(v) => updateDispatch.mutate({
                              locationId: loc.location_id,
                              flavorId: row.flavor_id,
                              amount: v,
                            })}
                          />
                          <td className="px-3 py-1.5 text-center text-gray-400 text-xs">
                            {row.sales_trend_median > 0
                              ? `${Math.round((1 - row.par_value / row.sales_trend_median) * 100)}%`
                              : "0%"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}

            {/* Amount to Bake summary — matches the bottom of the Dispatch PARs Google Sheet */}
            {bakeSummary.length > 0 && (
              <div className="bg-white rounded-xl border-2 border-cyan-300 shadow-sm overflow-hidden break-inside-avoid">
                <div className="bg-cyan-50 px-4 py-2 border-b border-cyan-200">
                  <h3 className="font-bold text-cyan-800">Amount to Bake for: {selectedDate}</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[700px]">
                    <thead>
                      <tr className="bg-gray-50 text-left border-b">
                        <th className="px-3 py-2 sticky left-0 bg-gray-50 z-10 font-semibold">Cookies</th>
                        {data.locations.map((loc) => (
                          <th key={loc.location_id} className="px-3 py-2 text-center font-semibold text-xs">
                            {loc.location_name}
                          </th>
                        ))}
                        <th className="px-3 py-2 text-center font-semibold text-xs bg-orange-50">Website Midnight-6PM</th>
                        <th className="px-3 py-2 text-center font-semibold text-xs bg-orange-50">Website 6:01PM-Midnight</th>
                        <th className="px-3 py-2 text-center font-bold bg-cyan-50 text-cyan-800">GRAND TOTAL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bakeSummary.map((row) => (
                        <tr key={row.flavorCode} className="border-b hover:bg-gray-50">
                          <td className="px-3 py-1.5 font-medium sticky left-0 bg-white z-10">
                            <span className="text-xs text-gray-400 mr-1">{row.flavorCode}</span>
                            {row.flavorName}
                          </td>
                          {row.perLocation.map((qty, i) => (
                            <td key={i} className="px-3 py-1.5 text-center">
                              {qty > 0 ? qty : <span className="text-gray-300">0</span>}
                            </td>
                          ))}
                          <td className="px-3 py-1.5 text-center bg-orange-50">
                            {row.web1 > 0 ? row.web1 : <span className="text-gray-300">0</span>}
                          </td>
                          <td className="px-3 py-1.5 text-center bg-orange-50">
                            {row.web2 > 0 ? row.web2 : <span className="text-gray-300">0</span>}
                          </td>
                          <td className="px-3 py-1.5 text-center font-bold bg-cyan-50 text-cyan-800 underline">
                            {row.grandTotal}
                          </td>
                        </tr>
                      ))}
                      {/* Totals row */}
                      <tr className="bg-gray-100 font-bold border-t-2">
                        <td className="px-3 py-2 sticky left-0 bg-gray-100 z-10">Total</td>
                        {data.locations.map((loc) => (
                          <td key={loc.location_id} className="px-3 py-2 text-center">
                            {loc.total_to_send}
                          </td>
                        ))}
                        <td className="px-3 py-2 text-center bg-orange-50">
                          {bakeSummary.reduce((s, r) => s + r.web1, 0)}
                        </td>
                        <td className="px-3 py-2 text-center bg-orange-50">
                          {bakeSummary.reduce((s, r) => s + r.web2, 0)}
                        </td>
                        <td className="px-3 py-2 text-center bg-cyan-100 text-cyan-900">
                          {bakeSummary.reduce((s, r) => s + r.grandTotal, 0)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="text-gray-400 text-center py-8">
            No dispatch plan for this date. Click &quot;Generate Plan&quot; to create one.
          </p>
        )}
      </div>
    </AppShell>
  );
}

interface BakeSummaryRow {
  flavorCode: string;
  flavorName: string;
  flavorId: number;
  perLocation: number[];
  web1: number;
  web2: number;
  grandTotal: number;
}

function buildBakeSummary(
  data: DispatchPlanResponse | undefined,
  webOrders?: { midnight_6pm: Record<string, number>; "6pm_midnight": Record<string, number> } | null,
): BakeSummaryRow[] {
  if (!data?.locations.length) return [];

  const flavors = data.locations[0].rows;

  return flavors.map((_, flavorIdx) => {
    const firstLoc = data.locations[0].rows[flavorIdx];
    const perLocation = data.locations.map((loc) => {
      const row = loc.rows[flavorIdx];
      return row.override_amount ?? row.amount_to_send;
    });
    const mallTotal = perLocation.reduce((sum, qty) => sum + qty, 0);
    const fid = String(firstLoc.flavor_id);
    const web1 = webOrders?.midnight_6pm?.[fid] ?? 0;
    const web2 = webOrders?.["6pm_midnight"]?.[fid] ?? 0;

    return {
      flavorCode: firstLoc.flavor_code,
      flavorName: firstLoc.flavor_name,
      flavorId: firstLoc.flavor_id,
      perLocation,
      web1,
      web2,
      grandTotal: mallTotal + web1 + web2,
    };
  });
}
