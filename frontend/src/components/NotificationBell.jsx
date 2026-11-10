import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { api } from "../api/client";
import { formatDateTime } from "../lib/format";

// bell with the unread count. checks for new ones every 60 seconds
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api("/notifications"),
    refetchInterval: 60_000,
  });

  // click outside closes the list
  useEffect(() => {
    const onClick = (e) => box.current && !box.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });

  async function openItem(n) {
    if (!n.is_read) await api(`/notifications/${n.id}/read`, { method: "POST" });
    refresh();
    setOpen(false);
    if (n.ticket_id) navigate(`/tickets/${n.ticket_id}`);
  }

  async function readAll() {
    await api("/notifications/read-all", { method: "POST" });
    refresh();
  }

  const unread = data?.unread ?? 0;
  return (
    <div className="relative" ref={box}>
      <button onClick={() => setOpen((o) => !o)} className="btn-secondary relative px-2.5 py-1.5" aria-label={`Notifications, ${unread} unread`}>
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -right-1.5 -top-1.5 min-w-[1.25rem] rounded-full bg-red-600 px-1 text-center text-[11px] font-semibold leading-5 text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="card absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden shadow-xl lg:left-0 lg:right-auto">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5 dark:border-slate-800">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 && <button onClick={readAll} className="text-xs text-brand-600 dark:text-brand-400 hover:underline">Mark all read</button>}
          </div>
          <ul className="max-h-96 overflow-y-auto">
            {!data?.items.length && <li className="px-4 py-6 text-center text-sm text-slate-500">Nothing yet.</li>}
            {data?.items.map((n) => (
              <li key={n.id}>
                <button onClick={() => openItem(n)} className={`block w-full px-4 py-3 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800 ${n.is_read ? "text-slate-500" : ""}`}>
                  <span className="flex items-start gap-2">
                    {!n.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />}
                    <span>
                      {n.message}
                      <span className="mt-0.5 block text-xs text-slate-400">{formatDateTime(n.created_at)}</span>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
