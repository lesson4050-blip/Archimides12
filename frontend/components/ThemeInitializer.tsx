"use client";

import { useEffect } from "react";

export default function ThemeInitializer() {
  useEffect(() => {
    const applyTheme = (theme: string) => {
      const html = document.documentElement;
      const body = document.body;
      html.classList.remove("light", "dark");
      body.classList.remove("light", "dark");

      let effectiveTheme = theme;
      if (theme === "system") {
        effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }

      html.classList.add(effectiveTheme);
      body.classList.add(effectiveTheme);
      html.setAttribute("data-theme", effectiveTheme);
    };

    const fetchAndApply = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/settings");
        if (res.ok) {
          const data = await res.json();
          if (data.theme) applyTheme(data.theme);
        }
      } catch (e) {
        // Fallback or silent fail
      }
    };

    fetchAndApply();

    // Listen for changes from the settings modal
    window.addEventListener("theme-change", (e: any) => {
      applyTheme(e.detail.theme);
    });
  }, []);

  return null;
}
