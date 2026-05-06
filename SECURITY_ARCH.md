# Archimedes Security Architecture & Audit Notes

## 🔴 Critical Architectural Risks

### 1. Docker Socket Exposure
**Risk**: The backend process currently mounts the Docker socket (`/var/run/docker.sock` or Windows Pipe).
**Impact**: If the backend is compromised, an attacker can gain full control over the Docker daemon, potentially leading to host takeover.
**Mitigation**: Sandbox isolation protects the host from the *agent*, but the *backend* itself is a privileged process. In production, this should be mitigated by using a remote Docker API with TLS or a restricted sidecar.

### 2. Sandbox Isolation (Docker vs MicroVM)
**Status**: Currently uses Docker containers with restricted capabilities (`cap_drop=['ALL']`, `no-new-privileges`).
**Limitation**: Docker is not a strong security boundary. A kernel vulnerability could allow a sandbox escape.
**Roadmap**: Implementation of Firecracker MicroVMs or gVisor is planned for high-stakes production environments.

## 🛡️ Implemented Safeguards (Audit Fixes - May 2026)

### 1. Path Traversal Protection
- **Mechanism**: `SandboxFilesystem` now uses `os.path.realpath` and `WORKSPACE_ROOT` validation.
- **Enforcement**: Any path outside `/home/ubuntu/workspace` triggers a `ValueError`.

### 2. Session Isolation (SharedBlackboard)
- **Mechanism**: Global state is now namespaced by `session_id`.
- **Enforcement**: `archimedes:blackboard:{session_id}:key` prevents data leakage between concurrent users.

### 3. Authentication Defaulting
- **Mechanism**: `AUTH_ENABLED` is now `True` by default in code and `.env`.
- **Enforcement**: System rejects all requests without a valid JWT unless explicitly disabled for local development.

### 4. Step Limit Hardening
- **Mechanism**: Split counters for `reasoning_steps` and `tool_call_steps`.
- **Benefit**: Prevents "infinite tool loops" while allowing complex tasks enough headroom to finish.

## ⚠️ Operational Security (OpSec)
- **.env Safety**: Never commit `.env` to version control. Always use the provided `.env.example`.
- **Key Rotation**: If an archive or log containing keys is exposed, **ROTATE ALL KEYS IMMEDIATELY**.
