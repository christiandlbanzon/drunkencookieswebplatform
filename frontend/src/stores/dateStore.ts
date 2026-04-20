import { create } from "zustand";
import { format } from "date-fns";

interface DateState {
  selectedDate: string; // YYYY-MM-DD
  setDate: (d: string) => void;
}

export const useDateStore = create<DateState>((set) => ({
  selectedDate: format(new Date(), "yyyy-MM-dd"),
  setDate: (d) => set({ selectedDate: d }),
}));
