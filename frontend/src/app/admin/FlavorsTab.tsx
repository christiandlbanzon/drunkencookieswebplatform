"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { useToast } from "@/components/shared/Toast";

interface ApiFlavor {
  id: number;
  code: string;
  name: string;
  sort_order: number;
  is_core: boolean;
  is_active: boolean;
  category: string;
}

export default function FlavorsTab() {
  const qc = useQueryClient();
  const toast = useToast();
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data: flavors, isLoading } = useQuery<ApiFlavor[]>({
    queryKey: ["admin-flavors"],
    queryFn: () => api.get("/admin/flavors").then((r) => r.data),
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: any }) => api.patch(`/admin/flavors/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-flavors"] });
      toast.show("Flavor updated");
      setEditingId(null);
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  const clearSales = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/flavors/${id}/sales-history`),
    onSuccess: (res: any) => {
      toast.show(`Cleared ${res.data?.records_deleted || 0} sales records`);
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-gray-500">
          Manage flavor slots A-N. Rename a flavor when launching a replacement
          (e.g., Guava Crumble → Linzer Cake). Toggle active/inactive to hide
          retired flavors. Use &quot;Clear Sales&quot; when reassigning a slot so old
          sales don&apos;t pollute the new flavor&apos;s median.
        </p>
      </div>

      {isLoading ? (
        <p className="text-gray-400 text-center py-8">Loading...</p>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-left">
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2">Active</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {flavors?.map((f) => (
                <tr key={f.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-bold text-cookie-700">{f.code}</td>
                  <td className="px-4 py-2">
                    {editingId === f.id ? (
                      <input
                        defaultValue={f.name}
                        className="border rounded px-2 py-0.5 text-sm w-full"
                        onBlur={(e) => {
                          if (e.target.value !== f.name) {
                            update.mutate({ id: f.id, body: { name: e.target.value } });
                          } else {
                            setEditingId(null);
                          }
                        }}
                        autoFocus
                      />
                    ) : (
                      <span onClick={() => setEditingId(f.id)} className="cursor-pointer hover:text-cookie-600">
                        {f.name}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{f.category}</td>
                  <td className="px-4 py-2">
                    <label className="inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={f.is_active}
                        onChange={(e) => update.mutate({ id: f.id, body: { is_active: e.target.checked } })}
                        className="h-4 w-4"
                      />
                    </label>
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button
                      onClick={() => setEditingId(editingId === f.id ? null : f.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      {editingId === f.id ? "Cancel" : "Rename"}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Clear ALL sales history for ${f.name}? This is irreversible and should only be done when reassigning the slot to a new flavor.`)) {
                          clearSales.mutate(f.id);
                        }
                      }}
                      className="text-red-600 hover:underline text-xs"
                    >
                      Clear Sales
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
