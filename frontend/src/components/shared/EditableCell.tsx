"use client";

import { useState } from "react";

interface EditableCellProps {
  value: number;
  onSave: (v: number) => void;
  highlight?: boolean;
  className?: string;
  min?: number;
  max?: number;
}

export default function EditableCell({
  value,
  onSave,
  highlight,
  className = "",
  min = 0,
  max = 10000,
}: EditableCellProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));
  const [error, setError] = useState(false);

  function handleSave() {
    const n = parseInt(draft, 10);
    if (isNaN(n) || n < min || n > max) {
      setError(true);
      setTimeout(() => setError(false), 1500);
      setEditing(false);
      return;
    }
    if (n !== value) onSave(n);
    setEditing(false);
  }

  if (editing) {
    return (
      <td className="px-1 py-1 text-center">
        <input
          type="number"
          value={draft}
          min={min}
          max={max}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={handleSave}
          onKeyDown={(e) => {
            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            if (e.key === "Escape") setEditing(false);
          }}
          className="w-16 text-center border-2 border-cookie-400 rounded px-1 py-0.5 text-sm focus:outline-none"
          autoFocus
        />
      </td>
    );
  }

  return (
    <td
      onClick={() => { setDraft(String(value)); setEditing(true); }}
      className={`px-3 py-1.5 text-center cursor-pointer hover:ring-1 hover:ring-green-400 transition ${
        error ? "bg-red-100 ring-1 ring-red-400" :
        highlight ? "bg-green-100 font-bold" :
        className ? className : "bg-green-50"
      }`}
      title="Click to edit"
    >
      {value}
    </td>
  );
}
