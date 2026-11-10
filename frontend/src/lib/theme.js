import { useEffect, useState } from "react";

const KEY = "echocampus.theme";

function initialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved) return saved;
  } catch {
    // storage blocked, fall back to the system setting
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// runs once at startup, so pages without the sidebar (login, register) get dark mode too
export function applySavedTheme() {
  document.documentElement.classList.toggle("dark", initialTheme() === "dark");
}

// light/dark switch, remembered in localStorage
export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      // fine, it just won't be remembered
    }
  }, [theme]);

  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}
