import { useEffect, useRef, useState } from "react";
import { Eye, FileText, UploadCloud, X } from "lucide-react";
import { formatSize } from "../lib/format";
import Modal from "./Modal";

export const MAX_MB = 5;
export const MAX_FILES = 5;
const ALLOWED = {
  "image/jpeg": "image", "image/png": "image", "image/webp": "image",
  "application/pdf": "pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
};

/**
 * picks files before upload. checks type/size/count here for quick feedback,
 * the backend checks again by real content (this check is only for the user)
 * items: [{ id, file, kind, url, progress, error }]
 */
export default function FileDropzone({ items, onChange, maxFiles = MAX_FILES, disabled }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [problems, setProblems] = useState([]);
  const [preview, setPreview] = useState(null);

  // free the local preview urls when the page closes (ref so we see the latest list)
  const latest = useRef(items);
  latest.current = items;
  useEffect(() => () => latest.current.forEach((i) => i.url && URL.revokeObjectURL(i.url)), []);

  function add(fileList) {
    const errors = [];
    const next = [...items];
    for (const file of fileList) {
      const kind = ALLOWED[file.type];
      if (!kind) errors.push(`${file.name}: only JPG, PNG, WEBP, PDF or DOCX`);
      else if (file.size > MAX_MB * 1024 * 1024) errors.push(`${file.name}: bigger than ${MAX_MB} MB`);
      else if (next.length >= maxFiles) errors.push(`${file.name}: max ${maxFiles} files`);
      else next.push({ id: crypto.randomUUID(), file, kind, url: kind !== "docx" ? URL.createObjectURL(file) : null, progress: 0 });
    }
    setProblems(errors);
    onChange(next);
  }

  function remove(id) {
    const item = items.find((i) => i.id === id);
    if (item?.url) URL.revokeObjectURL(item.url);
    onChange(items.filter((i) => i.id !== id));
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && input.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); if (!disabled) add(e.dataTransfer.files); }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition
          ${dragging ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40" : "border-slate-300 hover:border-indigo-400 dark:border-slate-700"}
          ${disabled ? "pointer-events-none opacity-60" : ""}`}
      >
        <UploadCloud className="mb-2 text-slate-400" size={28} />
        <p className="text-sm font-medium">Drop proof here or click to choose</p>
        <p className="mt-1 text-xs text-slate-500">JPG, PNG, WEBP, PDF or DOCX · up to {MAX_MB} MB each · max {maxFiles} files</p>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept=".jpg,.jpeg,.png,.webp,.pdf,.docx"
          onChange={(e) => { add(e.target.files); e.target.value = ""; }}
        />
      </div>

      {problems.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-red-600">{problems.map((p) => <li key={p}>{p}</li>)}</ul>
      )}

      {items.length > 0 && (
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {items.map((i) => (
            <li key={i.id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-2 dark:border-slate-800">
              {i.kind === "image" ? (
                <img src={i.url} alt="" className="h-12 w-12 shrink-0 rounded-md object-cover" />
              ) : (
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-slate-100 text-xs font-semibold uppercase text-slate-500 dark:bg-slate-800">
                  <FileText size={18} />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{i.file.name}</p>
                <p className="text-xs text-slate-500">{i.kind.toUpperCase()} · {formatSize(i.file.size)}</p>
                {i.progress > 0 && (
                  <div className="mt-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700">
                    <div className={`h-1.5 rounded-full ${i.error ? "bg-red-500" : "bg-indigo-500"}`} style={{ width: `${i.progress}%` }} />
                  </div>
                )}
                {i.error && <p className="text-xs text-red-600">{i.error}</p>}
              </div>
              {i.url && (
                <button type="button" onClick={() => setPreview(i)} className="text-slate-400 hover:text-indigo-600" aria-label="Preview">
                  <Eye size={16} />
                </button>
              )}
              {!disabled && (
                <button type="button" onClick={() => remove(i.id)} className="text-slate-400 hover:text-red-600" aria-label="Remove">
                  <X size={16} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {preview && (
        <Modal title={preview.file.name} onClose={() => setPreview(null)} wide>
          {preview.kind === "image" ? (
            <img src={preview.url} alt={preview.file.name} className="mx-auto max-h-[70vh] rounded-md" />
          ) : (
            <iframe src={preview.url} title={preview.file.name} className="h-[70vh] w-full rounded-md" />
          )}
        </Modal>
      )}
    </div>
  );
}
