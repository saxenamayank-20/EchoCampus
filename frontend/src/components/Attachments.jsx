import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, FileText, Paperclip } from "lucide-react";
import { api, fetchFileUrl, uploadFile } from "../api/client";
import { formatDateTime, formatSize, roleLabel } from "../lib/format";
import FileDropzone, { MAX_FILES } from "./FileDropzone";
import Modal from "./Modal";
import { useToast } from "./Toast";

const isImage = (a) => a.mime_type.startsWith("image/");
const isPdf = (a) => a.mime_type === "application/pdf";

function Thumb({ attachment }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let local;
    if (isImage(attachment)) {
      fetchFileUrl(attachment.id).then((u) => { local = u; setUrl(u); }).catch(() => {});
    }
    return () => local && URL.revokeObjectURL(local);
  }, [attachment]);

  if (url) return <img src={url} alt="" className="h-12 w-12 rounded-md object-cover" />;
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-md bg-slate-100 text-slate-500 dark:bg-slate-800">
      <FileText size={18} />
    </div>
  );
}

/** proof files on a ticket: list, preview, download, and (if allowed) add more */
export default function Attachments({ ticketId, canUpload }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { data: files = [], isLoading } = useQuery({
    queryKey: ["attachments", ticketId],
    queryFn: () => api(`/complaints/${ticketId}/attachments`),
  });
  const [preview, setPreview] = useState(null); // { attachment, url }
  const [pending, setPending] = useState([]);
  const [uploading, setUploading] = useState(false);

  async function open(attachment) {
    try {
      setPreview({ attachment, url: await fetchFileUrl(attachment.id) });
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function download(attachment) {
    try {
      const url = await fetchFileUrl(attachment.id);
      const a = document.createElement("a");
      a.href = url;
      a.download = attachment.original_name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function uploadPending() {
    setUploading(true);
    const left = [];
    for (const item of pending) {
      try {
        await uploadFile(ticketId, item.file, (p) =>
          setPending((all) => all.map((x) => (x.id === item.id ? { ...x, progress: p } : x))));
      } catch (e) {
        left.push({ ...item, error: e.message, progress: 100 });
      }
    }
    setUploading(false);
    setPending(left);
    queryClient.invalidateQueries({ queryKey: ["attachments", ticketId] });
    if (!left.length) toast.success("Proof uploaded.");
  }

  function closePreview() {
    URL.revokeObjectURL(preview.url);
    setPreview(null);
  }

  return (
    <div>
      {isLoading ? (
        <p className="text-sm text-slate-500">Loading files…</p>
      ) : files.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-slate-500"><Paperclip size={14} /> No proof attached.</p>
      ) : (
        <ul className="space-y-2">
          {files.map((f) => (
            <li key={f.id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-2 dark:border-slate-800">
              <Thumb attachment={f} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{f.original_name}</p>
                <p className="text-xs text-slate-500">
                  {formatSize(f.size_bytes)} · {roleLabel(f.uploader_role)} · {formatDateTime(f.created_at)}
                </p>
              </div>
              {(isImage(f) || isPdf(f)) && (
                <button onClick={() => open(f)} className="text-slate-400 hover:text-indigo-600" aria-label="Preview">
                  <Eye size={16} />
                </button>
              )}
              <button onClick={() => download(f)} className="text-slate-400 hover:text-indigo-600" aria-label="Download">
                <Download size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {canUpload && files.length < MAX_FILES && (
        <div className="mt-4 space-y-3">
          <FileDropzone items={pending} onChange={setPending} maxFiles={MAX_FILES - files.length} disabled={uploading} />
          {pending.length > 0 && (
            <button className="btn-primary" disabled={uploading} onClick={uploadPending}>
              {uploading ? "Uploading…" : `Upload ${pending.length} file${pending.length > 1 ? "s" : ""}`}
            </button>
          )}
        </div>
      )}

      {preview && (
        <Modal title={preview.attachment.original_name} onClose={closePreview} wide>
          {isImage(preview.attachment) ? (
            <img src={preview.url} alt="" className="mx-auto max-h-[70vh] rounded-md" />
          ) : (
            <iframe src={preview.url} title="preview" className="h-[70vh] w-full rounded-md" />
          )}
        </Modal>
      )}
    </div>
  );
}
