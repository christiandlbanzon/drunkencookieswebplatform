"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import { useToast } from "@/components/shared/Toast";

const ROLES = ["admin", "ops_manager", "kitchen", "dispatch", "store_manager"];

interface ApiUser {
  id: number;
  username: string;
  display_name: string;
  role: string;
  location_id: number | null;
  is_active: boolean;
}

export default function UsersTab() {
  const qc = useQueryClient();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", display_name: "", role: "kitchen", location_id: "" });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [resetPwd, setResetPwd] = useState<{ id: number; pwd: string } | null>(null);

  const { data: users, isLoading } = useQuery<ApiUser[]>({
    queryKey: ["admin-users"],
    queryFn: () => api.get("/admin/users").then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: (body: any) => api.post("/admin/users", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.show("User created");
      setShowForm(false);
      setForm({ username: "", password: "", display_name: "", role: "kitchen", location_id: "" });
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: any }) => api.patch(`/admin/users/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.show("User updated");
      setEditingId(null);
      setResetPwd(null);
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/users/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.show("User deleted");
    },
    onError: (err: any) => toast.show(err.response?.data?.detail || "Failed", "error"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Manage platform users and their roles.</p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-cookie-500 hover:bg-cookie-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          {showForm ? "Cancel" : "+ Add User"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <input placeholder="Display Name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {form.role === "store_manager" && (
              <input placeholder="Location ID (1-6)" value={form.location_id} onChange={(e) => setForm({ ...form, location_id: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            )}
          </div>
          <button
            onClick={() => create.mutate({ ...form, location_id: form.location_id ? Number(form.location_id) : null })}
            disabled={!form.username || !form.password || !form.display_name}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            Create User
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-center py-8">Loading...</p>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-left">
                <th className="px-4 py-2">ID</th>
                <th className="px-4 py-2">Username</th>
                <th className="px-4 py-2">Display Name</th>
                <th className="px-4 py-2">Role</th>
                <th className="px-4 py-2">Location</th>
                <th className="px-4 py-2">Active</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((u) => (
                <tr key={u.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-400">{u.id}</td>
                  <td className="px-4 py-2 font-medium">{u.username}</td>
                  <td className="px-4 py-2">
                    {editingId === u.id ? (
                      <input
                        defaultValue={u.display_name}
                        className="border rounded px-2 py-0.5 text-sm w-full"
                        onBlur={(e) => update.mutate({ id: u.id, body: { display_name: e.target.value } })}
                      />
                    ) : u.display_name}
                  </td>
                  <td className="px-4 py-2">
                    {editingId === u.id ? (
                      <select
                        defaultValue={u.role}
                        className="border rounded px-2 py-0.5 text-sm"
                        onChange={(e) => update.mutate({ id: u.id, body: { role: e.target.value } })}
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    ) : (
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.role === "admin" ? "bg-purple-100 text-purple-700" :
                        u.role === "ops_manager" ? "bg-blue-100 text-blue-700" :
                        u.role === "kitchen" ? "bg-cyan-100 text-cyan-700" :
                        u.role === "dispatch" ? "bg-yellow-100 text-yellow-700" :
                        "bg-green-100 text-green-700"
                      }`}>{u.role}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{u.location_id || "-"}</td>
                  <td className="px-4 py-2">
                    <label className="inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={u.is_active}
                        onChange={(e) => update.mutate({ id: u.id, body: { is_active: e.target.checked } })}
                        className="h-4 w-4"
                      />
                    </label>
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button
                      onClick={() => setEditingId(editingId === u.id ? null : u.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      {editingId === u.id ? "Done" : "Edit"}
                    </button>
                    <button
                      onClick={() => setResetPwd(resetPwd?.id === u.id ? null : { id: u.id, pwd: "" })}
                      className="text-orange-600 hover:underline text-xs"
                    >
                      Reset PW
                    </button>
                    {u.username !== "admin" && (
                      <button
                        onClick={() => {
                          if (confirm(`Delete user ${u.username}?`)) del.mutate(u.id);
                        }}
                        className="text-red-600 hover:underline text-xs"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {resetPwd && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex gap-2 items-center">
          <span className="text-sm">New password for user #{resetPwd.id}:</span>
          <input
            type="password"
            value={resetPwd.pwd}
            onChange={(e) => setResetPwd({ ...resetPwd, pwd: e.target.value })}
            className="border rounded-lg px-3 py-1 text-sm flex-1"
          />
          <button
            onClick={() => update.mutate({ id: resetPwd.id, body: { password: resetPwd.pwd } })}
            disabled={!resetPwd.pwd}
            className="bg-orange-600 text-white px-3 py-1 rounded-lg text-sm disabled:opacity-50"
          >
            Save
          </button>
          <button onClick={() => setResetPwd(null)} className="text-gray-500 text-sm">Cancel</button>
        </div>
      )}
    </div>
  );
}
