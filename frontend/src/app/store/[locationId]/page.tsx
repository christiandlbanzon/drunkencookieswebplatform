"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { useDateStore } from "@/stores/dateStore";
import AppShell from "@/components/layout/AppShell";
import EditableCell from "@/components/shared/EditableCell";
import ExportBar from "@/components/shared/ExportBar";
import { useToast } from "@/components/shared/Toast";
import type { InventoryResponse } from "@/lib/types";

export default function StoreLocationPage() {
  const params = useParams();
  const locationId = params.locationId as string;
  const { selectedDate } = useDateStore();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading } = useQuery<InventoryResponse>({
    queryKey: ["inventory", selectedDate, locationId],
    queryFn: () => api.get(`/inventory/${selectedDate}/${locationId}`).then((r) => r.data),
    refetchInterval: 60000,
  });

  const updateCell = useMutation({
    mutationFn: ({ flavorId, field, value }: { flavorId: number; field: string; value: number }) =>
      api.patch(`/inventory/${selectedDate}/${locationId}/${flavorId}`, { [field]: value }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["inventory", selectedDate, locationId] });
      if (res.data?.sync_warning) {
        toast.show(res.data.sync_warning, "error");
      } else {
        toast.show("Saved");
      }
    },
    onError: () => toast.show("Failed to save", "error"),
  });

  const requestDelivery = useMutation({
    mutationFn: () => api.post(`/inventory/delivery-request/${locationId}`, null, { params: { notes: "2nd delivery needed" } }),
    onSuccess: () => toast.show("2nd delivery requested!"),
    onError: () => toast.show("Failed to request delivery", "error"),
  });

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-xl font-bold">
              Store Dashboard {data ? `- ${data.location_name}` : ""}
            </h2>
            <p className="text-sm text-gray-500">{selectedDate}</p>
          </div>
          <div className="flex gap-2">
            <ExportBar
              filename={`inventory-${data?.location_name?.replace(/\s+/g, "_") || locationId}-${selectedDate}`}
              rows={data?.rows.map((r) => {
                const expected = r.opening_stock + r.second_delivery - r.live_sales - r.expired - r.flawed - r.used_as_display - r.given_away - r.production_waste;
                return {
                  code: r.flavor_code,
                  flavor: r.flavor_name,
                  begin: r.beginning_inventory,
                  sent: r.sent_cookies,
                  received: r.received_cookies,
                  opening: r.opening_stock,
                  live_sales: r.live_sales,
                  second_delivery: r.second_delivery,
                  expected,
                  closing: r.closing_inventory,
                  expired: r.expired,
                  flawed: r.flawed,
                  display: r.used_as_display,
                  given_away: r.given_away,
                  production: r.production_waste,
                };
              }) ?? []}
              labels={{
                code: "Code", flavor: "Flavor", begin: "Beginning Inv",
                sent: "Sent", received: "Received", opening: "Opening Stock",
                live_sales: "Live Sales", second_delivery: "2nd Delivery",
                expected: "Expected", closing: "Closing Inv",
                expired: "Expired", flawed: "Flawed",
                display: "Used as Display", given_away: "Given Away",
                production: "Production Waste",
              }}
              keys={["code","flavor","begin","sent","received","opening","live_sales","second_delivery","expected","closing","expired","flawed","display","given_away","production"]}
            />
            <button
              onClick={() => requestDelivery.mutate()}
              disabled={requestDelivery.isPending}
              className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 print:hidden"
            >
              {requestDelivery.isPending ? "Requesting..." : "Request 2nd Delivery"}
            </button>
          </div>
        </div>

        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : data?.rows.length ? (
          <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-sm border-collapse min-w-[1000px]">
              <thead>
                <tr className="bg-gray-100 text-left">
                  <th className="px-3 py-2 sticky left-0 bg-gray-100 z-10">Flavor</th>
                  <th className="px-3 py-2 text-center">Begin Inv.</th>
                  <th className="px-3 py-2 text-center">Sent</th>
                  <th className="px-3 py-2 text-center">Received</th>
                  <th className="px-3 py-2 text-center bg-blue-50">Opening</th>
                  <th className="px-3 py-2 text-center bg-green-50">Live Sales</th>
                  <th className="px-3 py-2 text-center">2nd Delivery</th>
                  <th className="px-3 py-2 text-center bg-orange-50">Expected</th>
                  <th className="px-3 py-2 text-center bg-gray-200">Closing</th>
                  <th className="px-3 py-2 text-center bg-yellow-50">Expired</th>
                  <th className="px-3 py-2 text-center bg-yellow-50">Flawed</th>
                  <th className="px-3 py-2 text-center bg-yellow-50">Display</th>
                  <th className="px-3 py-2 text-center bg-yellow-50">Given Away</th>
                  <th className="px-3 py-2 text-center bg-yellow-50">Production</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.flavor_id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-1.5 font-medium sticky left-0 bg-white z-10">
                      <span className="text-xs text-gray-400 mr-1">{row.flavor_code}</span>
                      {row.flavor_name}
                    </td>
                    <EditableCell
                      value={row.beginning_inventory}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "beginning_inventory", value: v })}
                    />
                    <EditableCell
                      value={row.sent_cookies}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "sent_cookies", value: v })}
                    />
                    <EditableCell
                      value={row.received_cookies}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "received_cookies", value: v })}
                    />
                    <td className="px-3 py-1.5 text-center bg-blue-50 font-medium">{row.opening_stock}</td>
                    <td className="px-3 py-1.5 text-center bg-green-50 font-medium text-green-700">{row.live_sales}</td>
                    <EditableCell
                      value={row.second_delivery}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "second_delivery", value: v })}
                    />
                    {(() => {
                      const expected = row.opening_stock + row.second_delivery - row.live_sales - row.expired - row.flawed - row.used_as_display - row.given_away - row.production_waste;
                      return (
                        <td className={`px-3 py-1.5 text-center bg-orange-50 font-medium ${expected < 0 ? "text-red-600" : ""}`}>
                          {expected}
                        </td>
                      );
                    })()}
                    <EditableCell
                      value={row.closing_inventory}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "closing_inventory", value: v })}
                      highlight
                    />
                    <EditableCell
                      value={row.expired}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "expired", value: v })}
                      className="bg-yellow-50"
                    />
                    <EditableCell
                      value={row.flawed}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "flawed", value: v })}
                      className="bg-yellow-50"
                    />
                    <EditableCell
                      value={row.used_as_display}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "used_as_display", value: v })}
                      className="bg-yellow-50"
                    />
                    <EditableCell
                      value={row.given_away}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "given_away", value: v })}
                      className="bg-yellow-50"
                    />
                    <EditableCell
                      value={row.production_waste}
                      onSave={(v) => updateCell.mutate({ flavorId: row.flavor_id, field: "production_waste", value: v })}
                      className="bg-yellow-50"
                    />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-400 text-center py-8">No inventory data for this date.</p>
        )}
      </div>
    </AppShell>
  );
}
