"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import AppShell from "@/components/layout/AppShell";
import ExportBar from "@/components/shared/ExportBar";
import { useToast } from "@/components/shared/Toast";

interface Order {
  id: number;
  order_number: string;
  order_date: string;
  customer_name: string;
  contact_phone: string;
  email: string;
  shipping_address: string;
  gift_message: string;
  items_summary: string;
  tracking_number: string;
  delivery_status: string;
  is_special_request: boolean;
  special_request_type: string;
  refund_status: string;
  refund_amount: number;
  refund_date: string | null;
  refund_reason: string;
  package_notes: string;
  feedback: string;
  endorsement: string;
  total_price: number;
  financial_status: string;
}

interface OrderList {
  orders: Order[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: {
    total: number;
    pending: number;
    in_transit: number;
    delivered: number;
    refunded: number;
    special: number;
  };
}

const STATUS_COLORS: Record<string, string> = {
  Pending: "bg-yellow-100 text-yellow-800",
  "In Transit": "bg-blue-100 text-blue-800",
  "Out for Delivery": "bg-indigo-100 text-indigo-800",
  Delivered: "bg-green-100 text-green-800",
  "Delivery Failed": "bg-red-100 text-red-800",
  Cancelled: "bg-gray-100 text-gray-600",
};

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState<Record<number, string>>({});

  const { data, isLoading } = useQuery<OrderList>({
    queryKey: ["orders", page, search, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "25" });
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      return api.get(`/orders?${params}`).then((r) => r.data);
    },
  });

  const updateOrder = useMutation({
    mutationFn: ({ orderNumber, body }: { orderNumber: string; body: Record<string, string> }) =>
      api.patch(`/orders/${orderNumber}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.show("Notes saved");
    },
    onError: () => toast.show("Failed to save", "error"),
  });

  const stats = data?.stats;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-xl font-bold">Shopify Orders</h2>
          <ExportBar
            filename={`shopify-orders-${new Date().toISOString().slice(0,10)}`}
            rows={data?.orders?.map((o) => ({
              order_number: o.order_number,
              order_date: o.order_date,
              customer: o.customer_name,
              email: o.email,
              phone: o.contact_phone,
              items: o.items_summary,
              total: o.total_price,
              status: o.delivery_status,
              tracking: o.tracking_number,
              refund_status: o.refund_status,
              refund_amount: o.refund_amount,
              notes: o.package_notes,
              feedback: o.feedback,
            })) ?? []}
            labels={{
              order_number: "Order #", order_date: "Date", customer: "Customer",
              email: "Email", phone: "Phone", items: "Items", total: "Total",
              status: "Delivery Status", tracking: "Tracking",
              refund_status: "Refund", refund_amount: "Refund Amount",
              notes: "Notes", feedback: "Feedback",
            }}
            keys={["order_number","order_date","customer","email","phone","items","total","status","tracking","refund_status","refund_amount","notes","feedback"]}
          />
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {[
              { label: "Total", value: stats.total, color: "bg-gray-50" },
              { label: "Pending", value: stats.pending, color: "bg-yellow-50" },
              { label: "In Transit", value: stats.in_transit, color: "bg-blue-50" },
              { label: "Delivered", value: stats.delivered, color: "bg-green-50" },
              { label: "Refunded", value: stats.refunded, color: "bg-red-50" },
              { label: "Special", value: stats.special, color: "bg-purple-50" },
            ].map((s) => (
              <div key={s.label} className={`${s.color} rounded-lg p-2 text-center`}>
                <p className="text-lg font-bold">{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          <input
            placeholder="Search order # or customer..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="border rounded-lg px-3 py-1.5 text-sm flex-1 min-w-[200px]"
          />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            <option value="">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="In Transit">In Transit</option>
            <option value="Out for Delivery">Out for Delivery</option>
            <option value="Delivered">Delivered</option>
            <option value="Delivery Failed">Failed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
        </div>

        {/* Table */}
        {isLoading ? (
          <p className="text-gray-400 text-center py-8">Loading...</p>
        ) : !data?.orders.length ? (
          <p className="text-gray-400 text-center py-8">No orders found.</p>
        ) : (
          <>
            <div className="overflow-x-auto -mx-4 px-4">
              <table className="w-full text-sm border-collapse min-w-[800px]">
                <thead>
                  <tr className="bg-gray-100 text-left">
                    <th className="px-3 py-2">Order #</th>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Customer</th>
                    <th className="px-3 py-2">Items</th>
                    <th className="px-3 py-2 text-center">Status</th>
                    <th className="px-3 py-2 text-right">Total</th>
                    <th className="px-3 py-2 text-center">Refund</th>
                  </tr>
                </thead>
                <tbody>
                  {data.orders.map((order) => (
                    <>
                      <tr
                        key={order.id}
                        onClick={() => setExpandedId(expandedId === order.id ? null : order.id)}
                        className="border-b hover:bg-gray-50 cursor-pointer"
                      >
                        <td className="px-3 py-2 font-medium">
                          {order.order_number}
                          {order.is_special_request && (
                            <span className="ml-1 text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full">
                              {order.special_request_type || "Special"}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-gray-500">{order.order_date}</td>
                        <td className="px-3 py-2">{order.customer_name}</td>
                        <td className="px-3 py-2 text-gray-500 max-w-[200px] truncate">{order.items_summary}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[order.delivery_status] || "bg-gray-100"}`}>
                            {order.delivery_status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right font-medium">${order.total_price.toFixed(2)}</td>
                        <td className="px-3 py-2 text-center">
                          {order.refund_status === "Yes" && (
                            <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">
                              ${order.refund_amount.toFixed(2)}
                            </span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded detail */}
                      {expandedId === order.id && (
                        <tr key={`${order.id}-detail`} className="bg-gray-50">
                          <td colSpan={7} className="px-4 py-3">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Contact</p>
                                <p>{order.contact_phone || "-"} | {order.email || "-"}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Shipping Address</p>
                                <p>{order.shipping_address || "-"}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Tracking</p>
                                <p>{order.tracking_number || "No tracking"}</p>
                              </div>
                              <div>
                                <p className="text-gray-400 text-xs mb-1">Gift Message</p>
                                <p className="italic">{order.gift_message || "-"}</p>
                              </div>
                              {order.refund_status === "Yes" && (
                                <div>
                                  <p className="text-gray-400 text-xs mb-1">Refund</p>
                                  <p className="text-red-600">${order.refund_amount.toFixed(2)} on {order.refund_date} — {order.refund_reason || "No reason"}</p>
                                </div>
                              )}
                              <div className="sm:col-span-2">
                                <p className="text-gray-400 text-xs mb-1">Items</p>
                                <p>{order.items_summary}</p>
                              </div>
                              <div className="sm:col-span-2 border-t pt-2 mt-1">
                                <p className="text-gray-400 text-xs mb-1">Notes (editable)</p>
                                <textarea
                                  value={editNotes[order.id] ?? order.package_notes}
                                  onChange={(e) => setEditNotes({ ...editNotes, [order.id]: e.target.value })}
                                  onBlur={() => {
                                    const val = editNotes[order.id];
                                    if (val !== undefined && val !== order.package_notes) {
                                      updateOrder.mutate({ orderNumber: order.order_number, body: { package_notes: val } });
                                    }
                                  }}
                                  className="w-full border rounded px-2 py-1 text-sm"
                                  rows={2}
                                  placeholder="Add package notes..."
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  Showing {(page - 1) * 25 + 1}-{Math.min(page * 25, data.total)} of {data.total}
                </p>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 border rounded text-sm disabled:opacity-30"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                    disabled={page === data.total_pages}
                    className="px-3 py-1 border rounded text-sm disabled:opacity-30"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
