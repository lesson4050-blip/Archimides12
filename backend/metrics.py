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
chroma_collection_size = Gauge(
    "chroma_collection_size", 
    "Number of documents in the ChromaDB collection"
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
