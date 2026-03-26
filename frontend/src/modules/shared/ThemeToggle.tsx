"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";

type ThemeMode = "light" | "dark";

const STORAGE_KEY = "viru-theme";

function applyTheme(theme: ThemeMode) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

function getPreferredTheme(): ThemeMode {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

export default function ThemeToggle() {
  const { t } = useI18n();
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const initial = getPreferredTheme();
    setIsDark(initial === "dark");
    applyTheme(initial);
  }, []);

  function onToggle(next: boolean) {
    const theme: ThemeMode = next ? "dark" : "light";
    setIsDark(next);
    applyTheme(theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }

  const title = isDark ? t("shared.theme.dark") : t("shared.theme.light");

  return (
    <label className="theme-switch" title={title}>
      <input
        className="theme-switch__checkbox"
        type="checkbox"
        checked={isDark}
        onChange={(event) => onToggle(event.target.checked)}
        aria-label={t("shared.a11y.changeTheme")}
      />
      <div className="theme-switch__container">
        <div className="theme-switch__circle-container">
          <div className="theme-switch__sun-moon-container">
            <div className="theme-switch__moon">
              <span className="theme-switch__spot" />
              <span className="theme-switch__spot" />
              <span className="theme-switch__spot" />
            </div>
          </div>
        </div>
        <div className="theme-switch__clouds" />
        <div className="theme-switch__stars-container">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            width="24"
            height="24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 2l1.35 3.3L17 6.6l-2.7 2.2.9 3.6L12 10.9 8.8 12.4l.9-3.6L7 6.6l3.65-1.3L12 2z" />
          </svg>
        </div>
      </div>
    </label>
  );
}
