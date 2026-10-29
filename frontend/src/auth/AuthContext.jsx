import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, setToken, setUnauthorizedHandler } from "../api/client";
import { useToast } from "../components/Toast";

const AuthContext = createContext(null);
const STORAGE_KEY = "echocampus.session";

// token lives in memory, sessionStorage only keeps it across a page refresh (gone when the tab closes)
function readSession() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY)) ?? null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    const saved = readSession();
    if (saved?.token) setToken(saved.token);
    return saved;
  });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();

  const logout = useCallback(
    (message) => {
      setToken(null);
      sessionStorage.removeItem(STORAGE_KEY);
      setSession(null);
      queryClient.clear();
      if (message) toast.info(message);
      navigate("/login", { replace: true });
    },
    [navigate, queryClient, toast],
  );

  useEffect(() => {
    setUnauthorizedHandler(() => logout("Your session expired, please log in again."));
  }, [logout]);

  const login = useCallback(async (userId, password) => {
    const data = await api("/auth/login", { method: "POST", body: { user_id: userId, password } });
    const next = { token: data.access_token, user: data.user };
    setToken(next.token);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
    return data.user;
  }, []);

  const value = useMemo(
    () => ({ user: session?.user ?? null, login, logout: () => logout() }),
    [session, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function homeFor(role) {
  return { student: "/student/tickets", grievance_manager: "/manager/queue", admin: "/admin" }[role] ?? "/login";
}
