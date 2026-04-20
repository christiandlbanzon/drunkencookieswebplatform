"use client";

interface ExportBarProps {
  /** Filename base (no extension) — e.g. "bake-plan-2026-04-19" */
  filename: string;
  /** Array of row objects. Keys become CSV headers. */
  rows: Record<string, any>[];
  /** Optional column label overrides: { key: "Pretty Label" } */
  labels?: Record<string, string>;
  /** Optional column key order. Default: keys of first row. */
  keys?: string[];
}

function toCSV(rows: Record<string, any>[], keys: string[], labels: Record<string, string>): string {
  const escape = (val: any): string => {
    if (val === null || val === undefined) return "";
    const s = String(val);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };
  const header = keys.map((k) => escape(labels[k] || k)).join(",");
  const body = rows.map((r) => keys.map((k) => escape(r[k])).join(",")).join("\n");
  return header + "\n" + body;
}

export default function ExportBar({ filename, rows, labels = {}, keys }: ExportBarProps) {
  function handleCSV() {
    if (!rows.length) return;
    const columnKeys = keys || Object.keys(rows[0]);
    const csv = toCSV(rows, columnKeys, labels);
    // Prepend UTF-8 BOM so Excel opens accents correctly
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex gap-2 print:hidden">
      <button
        onClick={() => window.print()}
        className="border border-gray-300 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition flex items-center gap-1.5"
        title="Print (use 'Save as PDF' in the print dialog for PDF export)"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Print / PDF
      </button>
      <button
        onClick={handleCSV}
        disabled={!rows.length}
        className="border border-gray-300 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition disabled:opacity-50 flex items-center gap-1.5"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        CSV
      </button>
    </div>
  );
}
