import { useCallback, useEffect, useState } from "react"

const STORAGE_KEY = "bhusuraksha-theme"

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === "light" || stored === "dark") return stored
  } catch {
    // localStorage unavailable (private mode, etc.) — fall through to system preference.
  }
  if (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches) {
    return "dark"
  }
  return "light"
}

/**
 * Persists the user's explicit choice (localStorage) and defaults to the
 * OS preference only when no explicit choice has been made yet. Applies
 * the `.dark` class to <html>, which index.css's `@custom-variant dark`
 * uses to drive every `dark:` Tailwind utility in the app.
 */
export function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Non-fatal — the choice just won't persist across reloads.
    }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"))
  }, [])

  return { theme, toggleTheme }
}
