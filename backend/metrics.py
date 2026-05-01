from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

# Agent Metrics
agent_requests_total = Counter(
    "agent_requests_total", 
    "Total number of agent requests", 
    ["agent_type", "status"]
)

agent_request_duration_seconds = Histogram(
    "agent_request_duration_seconds", 
    "Latency of agent requests in seconds"
)

# LLM Metrics
llm_requests_total = Counter(
    "llm_requests_total", 
    "Total number of LLM requests", 
    ["provider", "model", "status"]
)

# Vector DB Metrics
chroma_user_collection_size = Gauge(
    "chroma_user_collection_size",
    "Document count per user ChromaDB collection",
    ["user_id"]
)
chroma_total_docs = Gauge(
    "chroma_total_docs_all_users",
    "Total documents across all ChromaDB collections"
)

# WebSocket Metrics
active_websocket_connections = Gauge(
    "active_websocket_connections", 
    "Number of active WebSocket connections"
)

# HTTP Metrics
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", 
    "HTTP request latency", 
    ["method", "endpoint"]
)

http_requests_total = Counter(
    "http_requests_total", 
    "Total HTTP requests", 
    ["method", "endpoint", "status"]
)

# Sandbox / WarmPool
warm_pool_hits = Counter(
    "sandbox_warm_pool_hits_total",
    "Number of times a warm container was served instantly"
)
warm_pool_misses = Counter(
    "sandbox_warm_pool_misses_total",
    "Number of cold starts (warm pool was empty)"
)
warm_pool_size = Gauge(
    "sandbox_warm_pool_size",
    "Current number of containers in the warm pool"
)
active_sandboxes = Gauge(
    "sandbox_active_sessions_total",
    "Number of currently active sandbox sessions"
)

# Orchestrator
agent_tasks_total = Counter(
    "agent_tasks_total",
    "Total agent tasks started",
    ["strategy", "mode"]
)
agent_task_duration = Histogram(
    "agent_task_duration_seconds",
    "Agent task duration in seconds",
    ["strategy"],
    buckets=[1, 5, 15, 30, 60, 120, 300]
)
agent_timeouts_total = Counter(
    "agent_timeouts_total",
    "Number of agent tasks that hit the timeout"
)
agent_circuit_breaker_total = Counter(
    "agent_circuit_breaker_total",
    "Number of times circuit breaker tripped"
)
