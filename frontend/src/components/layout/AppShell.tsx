"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useDateStore } from "@/stores/dateStore";
import { NAV_ITEMS } from "@/lib/constants";
import NotificationBell from "@/components/shared/NotificationBell";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { role, displayName, logout, hydrate } = useAuthStore();
  const { selectedDate, setDate } = useDateStore();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    hydrate();
    setHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !role) router.replace("/login");
  }, [hydrated, role, router]);

  if (!hydrated || !role) return null;

  const visibleNav = NAV_ITEMS.filter((item) => item.roles.includes(role));

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <h1 className="font-bold text-lg text-cookie-600 hidden sm:block">DC Ops</h1>
          <nav className="flex gap-1">
            {visibleNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  pathname.startsWith(item.href)
                    ? "bg-cookie-100 text-cookie-700"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setDate(e.target.value)}
            className="px-2 py-1 border rounded text-sm"
          />
          <NotificationBell />
          <span className="text-sm text-gray-500 hidden sm:inline">{displayName}</span>
          <button
            onClick={() => { logout(); window.location.href = "/login"; }}
            className="text-sm text-gray-400 hover:text-red-500 transition"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="flex-1 p-4 max-w-7xl mx-auto w-full">{children}</main>
    </div>
  );
}
