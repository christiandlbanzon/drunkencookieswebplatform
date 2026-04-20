"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { ROLE_DEFAULT_ROUTES } from "@/lib/constants";

export default function Home() {
  const router = useRouter();
  const { role, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (role) {
      router.replace(ROLE_DEFAULT_ROUTES[role] || "/bake");
    } else {
      router.replace("/login");
    }
  }, [role, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-gray-500">Loading...</p>
    </div>
  );
}
