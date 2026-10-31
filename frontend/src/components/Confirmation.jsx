import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { MessageSquareWarning, Star } from "lucide-react";
import { api } from "../api/client";
import { formatDateTime } from "../lib/format";
import { ConfirmationBadge } from "./Badges";
import { useToast } from "./Toast";

// shown to everyone: what happened in the latest close-request round
export function ConfirmationSummary({ complaint }) {
  const c = complaint.confirmation;
  if (!c || complaint.status === "Closed") return null;
  return (
    <div className="space-y-2 rounded-xl border border-slate-200 p-4 text-sm dark:border-slate-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">Close request</span>
        <ConfirmationBadge confirmation={c} />
      </div>
      <p className="text-slate-600 dark:text-slate-300"><span className="text-slate-500">Manager's note:</span> {c.manager_note}</p>
      {c.response === "pending" && <p className="text-xs text-slate-500">Auto-confirms on {formatDateTime(c.due_at)} if the student doesn't answer.</p>}
      {c.response === "disputed" && (
        <p className="flex gap-2 rounded-lg bg-red-50 p-2 text-red-800 dark:bg-red-950 dark:text-red-200">
          <MessageSquareWarning size={16} className="mt-0.5 shrink-0" /> Student: {c.student_reason}
        </p>
      )}
    </div>
  );
}

// the student answers "was it fixed?"
export function StudentConfirmPanel({ complaint, onDone }) {
  const toast = useToast();
  const [choice, setChoice] = useState(null);   // "yes" | "no"
  const [rating, setRating] = useState(0);
  const [reason, setReason] = useState("");
  const answer = useMutation({
    mutationFn: (body) => api(`/complaints/${complaint.ticket_id}/confirm`, { method: "POST", body }),
    onSuccess: (_, body) => {
      toast.success(body.fixed ? "Thanks! The admin can now close it." : "Sent back to the manager.");
      onDone();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <section className="card border-indigo-200 p-5 dark:border-indigo-900">
      <h2 className="font-semibold">Was it really fixed?</h2>
      <p className="mt-1 text-sm text-slate-500">
        The manager marked this resolved: “{complaint.confirmation.manager_note}”. Please answer by {formatDateTime(complaint.confirmation.due_at)}.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className={choice === "yes" ? "btn-primary" : "btn-secondary"} onClick={() => setChoice("yes")}>Yes, it's fixed</button>
        <button className={choice === "no" ? "btn-danger" : "btn-secondary"} onClick={() => setChoice("no")}>No, still an issue</button>
      </div>

      {choice === "yes" && (
        <div className="mt-4 space-y-3">
          <p className="text-sm">How happy are you with how it was handled? (optional)</p>
          <div className="flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" onClick={() => setRating(n)} aria-label={`${n} stars`}>
                <Star size={26} className={n <= rating ? "fill-amber-400 text-amber-400" : "text-slate-300"} />
              </button>
            ))}
          </div>
          <button className="btn-primary" disabled={answer.isPending}
            onClick={() => answer.mutate({ fixed: true, rating: rating || null })}>Confirm</button>
        </div>
      )}
      {choice === "no" && (
        <div className="mt-4 space-y-3">
          <label className="label" htmlFor="why">What's still wrong?</label>
          <textarea id="why" rows={3} className="input" value={reason} onChange={(e) => setReason(e.target.value)} />
          <p className="text-xs text-slate-500">You can also add new proof in the Proof section below.</p>
          <button className="btn-danger" disabled={!reason.trim() || answer.isPending}
            onClick={() => answer.mutate({ fixed: false, reason })}>Send back to the manager</button>
        </div>
      )}
    </section>
  );
}
