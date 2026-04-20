"use client";

import { useEffect, useState } from "react";
import { create } from "zustand";

interface ToastState {
  message: string | null;
  type: "success" | "error";
  show: (msg: string, type?: "success" | "error") => void;
  clear: () => void;
}

export const useToast = create<ToastState>((set) => ({
  message: null,
  type: "success",
  show: (msg, type = "success") => {
    set({ message: msg, type });
    const duration = type === "error" ? 5000 : 2500;
    setTimeout(() => set({ message: null }), duration);
  },
  clear: () => set({ message: null }),
}));

export default function Toast() {
  const { message, type } = useToast();

  if (!message) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-fade-in">
      <div
        className={`px-4 py-2 rounded-lg shadow-lg text-sm font-medium text-white ${
          type === "success" ? "bg-green-600" : "bg-red-600"
        }`}
      >
        {message}
      </div>
    </div>
  );
}
