"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import UsersTab from "./UsersTab";
import FlavorsTab from "./FlavorsTab";
import ParSettingsTab from "./ParSettingsTab";

const TABS = [
  { id: "users", label: "Users" },
  { id: "flavors", label: "Flavors" },
  { id: "par", label: "PAR Settings" },
];

export default function AdminPage() {
  const [tab, setTab] = useState("users");

  return (
    <AppShell>
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Admin</h2>
        <div className="flex gap-1 border-b">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                tab === t.id
                  ? "border-cookie-500 text-cookie-700"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {tab === "users" && <UsersTab />}
        {tab === "flavors" && <FlavorsTab />}
        {tab === "par" && <ParSettingsTab />}
      </div>
    </AppShell>
  );
}
