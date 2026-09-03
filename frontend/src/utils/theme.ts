/**
 * Applies the given theme by toggling the `dark` class on <html>
 * and persisting the value to localStorage["theme"].
 */
export function applyTheme(theme: "dark" | "light"): void {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  localStorage.setItem("theme", theme);
}

/**
 * Reads the stored theme from localStorage, defaulting to "light".
 */
export function readTheme(): "dark" | "light" {
  const stored = localStorage.getItem("theme");
  if (stored === "dark" || stored === "light") {
    return stored;
  }
  return "light";
}
