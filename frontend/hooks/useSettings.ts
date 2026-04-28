"use client";

import { useEffect } from "react";
import { useSettingsStore } from "@/lib/settingsStore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export function useSettings(isOpen: boolean) {
  const store = useSettingsStore();
  const { settings, setSettings, setUsageRecords, setLoading, setIsUpdating } = store;

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      fetchUsage();
    }
  }, [isOpen]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings`);
      if (!res.ok) throw new Error("Backend offline");
      const data = await res.json();
      setSettings(data);
      if (data.theme) applyTheme(data.theme);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch settings", err);
      setSettings({
        nickname: "Developer",
        theme: "dark",
        credits_remaining: 300,
        skills_json: {},
        connectors_json: {},
        integrations_json: {}
      });
      setLoading(false);
    }
  };

  const fetchUsage = async () => {
     try {
       const res = await fetch(`${API_BASE}/api/v1/settings/usage`);
       const data = await res.json();
       setUsageRecords(data);
     } catch (err) {
       console.error("Failed to fetch usage", err);
     }
  };

  const updateSettings = async (updates: any) => {
    setIsUpdating("global");
    const prevSettings = { ...settings };
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);

    try {
      const res = await fetch(`${API_BASE}/api/v1/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates)
      });
      const data = await res.json();
      setSettings(data);
      
      if (updates.theme) {
         applyTheme(updates.theme);
      }
    } catch (err) {
      console.error("Failed to update settings", err);
      setSettings(prevSettings);
    } finally {
      setIsUpdating(null);
    }
  };

  const applyTheme = (theme: string) => {
     const html = document.documentElement;
     const body = document.body;
     html.classList.remove("light", "dark");
     body.classList.remove("light", "dark");
     
     let effectiveTheme = theme;
     if (theme === "system") {
        effectiveTheme = typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
     }
     
     html.classList.add(effectiveTheme);
     body.classList.add(effectiveTheme);
     html.setAttribute("data-theme", effectiveTheme);
     
     if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("theme-change", { detail: { theme: effectiveTheme } }));
     }
  };

  return { fetchSettings, fetchUsage, updateSettings, applyTheme };
}
