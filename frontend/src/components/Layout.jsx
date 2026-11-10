import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import {
  BarChart3, BookOpen, CheckSquare, ChevronDown, Cpu, FilePlus2, Inbox, LayoutList, LogOut, Megaphone, Menu, MessageCircleQuestion,
  Moon, Sun, Ticket, UserRound, Users, X,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { roleLabel } from "../lib/format";
import { useTheme } from "../lib/theme";
import NotificationBell from "./NotificationBell";

const NAV = {
  student: [
    { to: "/student/new", label: "New complaint", icon: FilePlus2 },
    { to: "/student/tickets", label: "My tickets", icon: Ticket },
    { to: "/student/assistant", label: "Ask a question", icon: MessageCircleQuestion },
  ],
  // complaints opens the overview (small boxes) and drops down active / resolved under it
  grievance_manager: [
    {
      to: "/manager", label: "Complaints", icon: Inbox, children: [
        // match: still highlighted when a box added a filter like ?priority=Critical
        { to: "/manager/queue", label: "Active", match: (l) => l.pathname === "/manager/queue" && !l.search.includes("tab=resolved") },
        { to: "/manager/queue?tab=resolved", label: "Resolved", match: (l) => l.pathname === "/manager/queue" && l.search.includes("tab=resolved") },
      ],
    },
  ],
  admin: [
    { to: "/admin", label: "Overview", icon: BarChart3, end: true },
    { to: "/admin/complaints", label: "All complaints", icon: LayoutList },
    { to: "/admin/close-requests", label: "Close requests", icon: CheckSquare },
    { to: "/admin/updates", label: "Manager updates", icon: Megaphone },
    { to: "/admin/users", label: "Users", icon: Users },
    { to: "/admin/policies", label: "Policies", icon: BookOpen },
    { to: "/admin/ai-usage", label: "AI usage", icon: Cpu },
  ],
};

// every role gets this one at the end
const ACCOUNT = { to: "/account", label: "My account", icon: UserRound };

function isActive(location, to, end) {
  const [path, query] = to.split("?");
  if (query) return location.pathname === path && location.search === `?${query}`;
  if (end) return location.pathname === path && !location.search;
  return location.pathname.startsWith(path);
}

function NavLink({ to, label, icon: Icon, end, match, location, onNavigate }) {
  return (
    <Link
      to={to}
      onClick={onNavigate}
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
        (match ? match(location) : isActive(location, to, end))
          ? "bg-brand-100 font-medium text-brand-800 dark:bg-brand-400/10 dark:text-brand-400"
          : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
      }`}
    >
      {Icon && <Icon size={18} />}
      {label}
    </Link>
  );
}

// a link with a drop down: clicking it opens its page and shows the sub links
function NavGroup({ to, label, icon: Icon, items, location, onNavigate }) {
  const insideChild = items.some((c) => location.pathname === c.to.split("?")[0]);
  const [open, setOpen] = useState(insideChild);
  const here = location.pathname === to;

  // opening a list another way (a box on the overview, back button) also opens the drop down
  useEffect(() => {
    if (insideChild) setOpen(true);
  }, [insideChild]);

  return (
    <div>
      <Link
        to={to}
        onClick={() => setOpen((o) => (here ? !o : true))}
        aria-expanded={open}
        className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
          here
            ? "bg-brand-100 font-medium text-brand-800 dark:bg-brand-400/10 dark:text-brand-400"
            : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        }`}
      >
        <Icon size={18} />
        <span className="flex-1">{label}</span>
        <ChevronDown size={16} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </Link>
      {open && (
        <div className="ml-5 mt-1 space-y-1 border-l border-slate-200 pl-3 dark:border-slate-700">
          {items.map((c) => <NavLink key={c.to} {...c} location={location} onNavigate={onNavigate} />)}
        </div>
      )}
    </div>
  );
}

function Sidebar({ onNavigate }) {
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const location = useLocation();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-5 py-5">
        <img src="/favicon.svg" alt="" className="h-8 w-8" />
        <span className="flex-1 text-lg font-semibold">EchoCampus</span>
        {!onNavigate && <NotificationBell />}
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {[...NAV[user.role], ACCOUNT].map(({ to, label, icon: Icon, end, children }) =>
          children ? (
            <NavGroup key={to} to={to} label={label} icon={Icon} items={children} location={location} onNavigate={onNavigate} />
          ) : (
            <NavLink key={to} to={to} label={label} icon={Icon} end={end} location={location} onNavigate={onNavigate} />
          ),
        )}
      </nav>

      <div className="border-t border-slate-200 p-4 dark:border-slate-800">
        <div className="mb-3">
          <p className="truncate text-sm font-medium">{user.name}</p>
          <p className="text-xs text-slate-500">
            {user.user_id} · {roleLabel(user.role)}
          </p>
          {user.categories?.length > 0 && <p className="mt-1 text-xs text-slate-500">{user.categories.join(", ")}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={toggleTheme} className="btn-secondary flex-1 px-2" aria-label="Toggle dark mode">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button onClick={logout} className="btn-secondary flex-[3]">
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen lg:flex">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:block">
        <Sidebar />
      </aside>

      {/* mobile top bar + slide-in menu */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 lg:hidden">
        <span className="flex items-center gap-2 font-semibold"><img src="/favicon.svg" alt="" className="h-7 w-7" />EchoCampus</span>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <button onClick={() => setOpen(true)} aria-label="Open menu" className="btn-secondary px-2.5 py-1.5">
            <Menu size={18} />
          </button>
        </div>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl dark:bg-slate-900">
            <button onClick={() => setOpen(false)} aria-label="Close menu" className="absolute right-3 top-4 text-slate-500">
              <X size={20} />
            </button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}
