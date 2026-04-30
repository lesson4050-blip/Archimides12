"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, X, ChevronDown, ChevronUp, Plug, Unplug, Key, ExternalLink } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const NANGO_HOST = process.env.NEXT_PUBLIC_NANGO_HOST || "http://localhost:3003";
const NANGO_PUBLIC_KEY = process.env.NEXT_PUBLIC_NANGO_PUBLIC_KEY || "";

interface Service {
  name: string;
  icon: string;
  category: string;
  description: string;
  auth_type: "oauth" | "token";
  connected: boolean;
  capabilities: string[];
  nango_key: string;
}

interface ConnectorsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = "all" | string;

export default function ConnectorsPanel({ isOpen, onClose }: ConnectorsPanelProps) {
  const [services, setServices] = useState<Record<string, Service>>({});
  const [categories, setCategories] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<TabType>("all");
  const [loading, setLoading] = useState(true);
  const [tokenInputs, setTokenInputs] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState<string | null>(null);
  const [expandedService, setExpandedService] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const authHeader = () => ({
    Authorization: `Bearer ${localStorage.getItem("token")}`,
    "Content-Type": "application/json",
  });

  const fetchCatalog = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/connectors/catalog`, {
        headers: authHeader(),
      });
      const data = await r.json();
      setServices(data.services || {});
      setCategories(data.categories || {});
    } catch (e) {
      console.error("Failed to fetch connector catalog:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) fetchCatalog();
  }, [isOpen, fetchCatalog]);

  // OAuth connect via Nango frontend SDK (Connect Session Token pattern)
  const connectOAuth = async (serviceId: string, service: Service) => {
    setConnecting(serviceId);
    try {
      // Pre-check: verify Nango server is reachable before opening popup
      try {
        await Promise.race([
          fetch(`${NANGO_HOST}/health`, { method: "GET", mode: "no-cors" }),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error("timeout")), 5000)
          ),
        ]);
      } catch {
        alert(
          `Nango server is not available at ${NANGO_HOST}.\n\nPlease start Nango first:\n  docker-compose -f docker-compose.nango.yml up -d`
        );
        setConnecting(null);
        return;
      }

      // 1. Get a short-lived session token from our backend
      const tokenRes = await fetch(`${API_BASE}/api/v1/connectors/session-token`, {
        headers: authHeader(),
      });
      if (!tokenRes.ok) {
        throw new Error(`Failed to get session token: ${await tokenRes.text()}`);
      }
      const { token: sessionToken } = await tokenRes.json();

      // 2. Initialize Nango SDK with the session token (not publicKey)
      const NangoModule = await import("@nangohq/frontend");
      const Nango = NangoModule.default;
      const nangoSDK = new Nango({ host: NANGO_HOST, connectSessionToken: sessionToken } as any);

      // 3. Trigger the OAuth flow (connectionId not needed with session token)
      const result = await Promise.race([
        nangoSDK.auth(service.nango_key, `archimedes-${Date.now()}`),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error(
            `OAuth timed out. Make sure you have configured OAuth credentials for "${service.name}" in the Nango dashboard (http://localhost:3003).`
          )), 15000)
        ),
      ]);

      await fetchCatalog();

      // Trigger MCP sync
      await fetch(`${API_BASE}/api/v1/connectors/sync`, {
        method: "POST",
        headers: authHeader(),
      });
    } catch (e: any) {
      if (!e.message?.includes("cancelled")) {
        console.error("OAuth connect error:", e);
        alert(`Connection failed: ${e.message}`);
      }
    } finally {
      setConnecting(null);
    }
  };

  // Token connect
  const connectToken = async (serviceId: string) => {
    const token = tokenInputs[serviceId];
    if (!token?.trim()) return;
    setConnecting(serviceId);
    try {
      const r = await fetch(`${API_BASE}/api/v1/connectors/connect/token`, {
        method: "POST",
        headers: authHeader(),
        body: JSON.stringify({ service_id: serviceId, api_key: token }),
      });
      if (!r.ok) throw new Error(await r.text());
      setTokenInputs((v) => ({ ...v, [serviceId]: "" }));
      await fetchCatalog();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setConnecting(null);
    }
  };

  const disconnect = async (serviceId: string) => {
    if (!confirm(`Disconnect ${services[serviceId]?.name}?`)) return;
    await fetch(`${API_BASE}/api/v1/connectors/disconnect/${serviceId}`, {
      method: "POST",
      headers: authHeader(),
    });
    await fetchCatalog();
  };

  // Filter services
  const filteredServices = Object.entries(services).filter(([id, s]) => {
    const matchCat = activeTab === "all" || s.category === activeTab;
    const matchSearch =
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });

  const connectedCount = Object.values(services).filter((s) => s.connected).length;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="relative flex flex-col w-full max-w-3xl max-h-[85vh] rounded-2xl overflow-hidden"
        style={{
          background: "linear-gradient(165deg, #0a0a1a 0%, #0d0d20 50%, #0a0a18 100%)",
          border: "1px solid rgba(124, 111, 255, 0.15)",
          boxShadow: "0 0 80px rgba(124, 111, 255, 0.08), 0 25px 50px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                style={{
                  background: "linear-gradient(135deg, #7C6FFF 0%, #B8B0FF 100%)",
                  boxShadow: "0 0 20px rgba(124, 111, 255, 0.3)",
                }}
              >
                🔌
              </div>
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">Connectors</h2>
                <p className="text-xs text-gray-500">
                  Connect services — Archimedes uses them automatically
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {connectedCount > 0 && (
                <span
                  className="text-xs px-3 py-1 rounded-full font-medium"
                  style={{ background: "rgba(34, 197, 94, 0.12)", color: "#22C55E" }}
                >
                  {connectedCount} active
                </span>
              )}
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search 80+ services..."
              className="w-full text-sm pl-9 pr-4 py-2.5 rounded-xl outline-none transition-all focus:ring-1 focus:ring-[#7C6FFF]/40"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "white",
              }}
            />
          </div>
        </div>

        {/* Category tabs */}
        <div
          className="flex gap-1.5 px-5 py-3 overflow-x-auto flex-shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        >
          <button
            onClick={() => setActiveTab("all")}
            className="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all"
            style={{
              background: activeTab === "all" ? "linear-gradient(135deg, #7C6FFF, #9B8FFF)" : "rgba(255,255,255,0.04)",
              color: activeTab === "all" ? "white" : "#94A3B8",
              border: `1px solid ${activeTab === "all" ? "transparent" : "rgba(255,255,255,0.08)"}`,
            }}
          >
            All ({Object.keys(services).length})
          </button>
          {Object.entries(categories).map(([id, cat]: any) => {
            const count = Object.values(services).filter((s: any) => s.category === id).length;
            if (count === 0) return null;
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all"
                style={{
                  background:
                    activeTab === id ? "linear-gradient(135deg, #7C6FFF, #9B8FFF)" : "rgba(255,255,255,0.04)",
                  color: activeTab === id ? "white" : "#94A3B8",
                  border: `1px solid ${activeTab === id ? "transparent" : "rgba(255,255,255,0.08)"}`,
                }}
              >
                {cat.icon} {cat.name} ({count})
              </button>
            );
          })}
        </div>

        {/* Services list */}
        <div className="flex-1 overflow-y-auto px-5 py-4 custom-scrollbar">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-[#7C6FFF] border-t-transparent animate-spin" />
              <span className="text-gray-500 text-sm">Loading connectors...</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {filteredServices.map(([id, service]) => (
                <div
                  key={id}
                  className="group transition-all duration-200"
                  style={{
                    background: service.connected
                      ? "rgba(124, 111, 255, 0.04)"
                      : "rgba(255,255,255,0.02)",
                    border: `1px solid ${service.connected ? "rgba(124, 111, 255, 0.2)" : "rgba(255,255,255,0.06)"}`,
                    borderRadius: "14px",
                  }}
                >
                  {/* Main row */}
                  <div className="flex items-center gap-3 px-4 py-3.5">
                    <span className="text-2xl flex-shrink-0 w-9 h-9 flex items-center justify-center">
                      {service.icon}
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm text-white">{service.name}</span>
                        {service.connected && (
                          <span
                            className="text-[10px] px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1"
                            style={{ background: "rgba(34, 197, 94, 0.12)", color: "#22C55E" }}
                          >
                            <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                            Connected
                          </span>
                        )}
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                          style={{
                            background: "rgba(124, 111, 255, 0.08)",
                            color: "#B8B0FF",
                          }}
                        >
                          {service.auth_type === "oauth" ? "OAuth" : "API Key"}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{service.description}</p>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {/* Expand capabilities */}
                      <button
                        onClick={() => setExpandedService(expandedService === id ? null : id)}
                        className="text-gray-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
                      >
                        {expandedService === id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>

                      {service.connected ? (
                        <button
                          onClick={() => disconnect(id)}
                          className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 hover:bg-red-500/10"
                          style={{ color: "#EF4444", border: "1px solid rgba(239, 68, 68, 0.2)" }}
                        >
                          <Unplug size={12} />
                          Disconnect
                        </button>
                      ) : (
                        <>
                          {service.auth_type === "oauth" ? (
                            <button
                              onClick={() => connectOAuth(id, service)}
                              disabled={connecting === id}
                              className="text-xs px-4 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5"
                              style={{
                                background:
                                  connecting === id
                                    ? "rgba(124, 111, 255, 0.3)"
                                    : "linear-gradient(135deg, #7C6FFF, #9B8FFF)",
                                color: "white",
                                opacity: connecting === id ? 0.6 : 1,
                                boxShadow: connecting === id ? "none" : "0 0 15px rgba(124, 111, 255, 0.2)",
                              }}
                            >
                              {connecting === id ? (
                                <div className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                              ) : (
                                <Plug size={12} />
                              )}
                              {connecting === id ? "Connecting..." : "Connect"}
                            </button>
                          ) : (
                            <div className="flex gap-1.5">
                              <input
                                type="password"
                                placeholder="API Key..."
                                value={tokenInputs[id] || ""}
                                onChange={(e) =>
                                  setTokenInputs((v) => ({ ...v, [id]: e.target.value }))
                                }
                                className="text-xs px-3 py-1.5 rounded-lg outline-none w-32 transition-all focus:ring-1 focus:ring-[#7C6FFF]/40"
                                style={{
                                  background: "rgba(255,255,255,0.04)",
                                  border: "1px solid rgba(255,255,255,0.08)",
                                  color: "white",
                                }}
                              />
                              <button
                                onClick={() => connectToken(id)}
                                disabled={connecting === id || !tokenInputs[id]}
                                className="text-xs px-3 py-1.5 rounded-lg font-medium flex items-center gap-1"
                                style={{
                                  background:
                                    connecting === id || !tokenInputs[id]
                                      ? "rgba(124, 111, 255, 0.2)"
                                      : "linear-gradient(135deg, #7C6FFF, #9B8FFF)",
                                  color: "white",
                                  opacity: connecting === id || !tokenInputs[id] ? 0.5 : 1,
                                }}
                              >
                                <Key size={11} />
                                {connecting === id ? "..." : "Save"}
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Expanded capabilities */}
                  {expandedService === id && (
                    <div
                      className="px-4 pb-4 pt-2"
                      style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}
                    >
                      <p className="text-xs text-gray-500 mb-2.5 font-medium">
                        What Archimedes can do with {service.name}:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {service.capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="text-[11px] px-2.5 py-1 rounded-lg transition-colors"
                            style={{
                              background: "rgba(255,255,255,0.04)",
                              color: "#B8B0FF",
                              border: "1px solid rgba(124, 111, 255, 0.1)",
                            }}
                          >
                            {cap.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {filteredServices.length === 0 && (
                <div className="text-center py-16 text-sm text-gray-500">
                  No services found for &ldquo;{searchQuery}&rdquo;
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 flex items-center justify-between" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <span className="text-xs text-gray-600">
            {Object.keys(services).length} services available • Powered by Nango
          </span>
          <a
            href="https://docs.nango.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-[#B8B0FF] transition-colors flex items-center gap-1"
          >
            <ExternalLink size={11} />
            Docs
          </a>
        </div>
      </div>
    </div>
  );
}
