import logging
import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class K8sPodConfig:
    image: str = "archimedes/sandbox:latest"
    cpu_limit: str = "2"
    mem_limit: str = "4Gi"
    timeout_seconds: int = 3600
    env: Dict[str, str] = None

class KubernetesManager:
    """
    Zero-Bug Kubernetes Native Orchestrator for Archimedes 12.
    Replaces local Docker socket with production-grade K8s Jobs/Pods API.
    Provides unbounded scale for DAG-Swarm workers.
    """
    def __init__(self, namespace: str = "archimedes-sandboxes"):
        self.namespace = namespace
        self._client_initialized = False
        self._core_api = None
        self._batch_api = None
        
        # We fail gracefully if kubernetes package is missing (so it can still run locally)
        try:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
            
            self._core_api = client.CoreV1Api()
            self._batch_api = client.BatchV1Api()
            self._client_initialized = True
            logger.info("✅ Kubernetes API client initialized successfully.")
        except ImportError:
            logger.warning("Kubernetes Python client not installed. K8sManager is in dry-run/mock mode.")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes API: {e}")

    async def spawn_sandbox(self, session_id: str, config: Optional[K8sPodConfig] = None) -> Dict[str, Any]:
        """Spawns an isolated sandbox Pod/Job in Kubernetes."""
        if not config:
            config = K8sPodConfig()
            
        pod_name = f"sandbox-{session_id[:12]}-{uuid.uuid4().hex[:6]}"
        logger.info(f"Spawning K8s sandbox pod: {pod_name}")
        
        if not self._client_initialized:
            logger.warning("K8s client not available, returning mock K8s sandbox info.")
            return {
                "sandbox_id": pod_name,
                "status": "mocked",
                "internal_ip": "127.0.0.1",
                "port_9222": 9222
            }

        from kubernetes.client import V1Pod, V1PodSpec, V1Container, V1ResourceRequirements, V1ObjectMeta, V1SecurityContext, V1PodSecurityContext
        
        container = V1Container(
            name="sandbox",
            image=config.image,
            resources=V1ResourceRequirements(
                limits={"cpu": config.cpu_limit, "memory": config.mem_limit},
                requests={"cpu": "0.5", "memory": "1Gi"}
            ),
            security_context=V1SecurityContext(
                allow_privilege_escalation=False,
                run_as_non_root=True,
                run_as_user=1000,
                read_only_root_filesystem=False
            ),
            # Keep alive
            command=["tail", "-f", "/dev/null"],
            env=[{"name": k, "value": v} for k, v in (config.env or {}).items()]
        )
        
        pod = V1Pod(
            metadata=V1ObjectMeta(name=pod_name, labels={"app": "archimedes-sandbox", "session": session_id}),
            spec=V1PodSpec(
                containers=[container], 
                restart_policy="Never",
                security_context=V1PodSecurityContext(
                    fs_group=1000,
                    run_as_user=1000,
                    run_as_non_root=True
                )
            )
        )

        try:
            # Run in threadpool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._core_api.create_namespaced_pod, self.namespace, pod)
            
            # Wait for pod IP
            pod_ip = await self._wait_for_pod_ip(pod_name)
            
            return {
                "sandbox_id": pod_name,
                "status": "running",
                "internal_ip": pod_ip,
                "port_9222": 9222  # TCP IPC port
            }
        except Exception as e:
            logger.error(f"Failed to spawn K8s sandbox {pod_name}: {e}")
            raise

    async def _wait_for_pod_ip(self, pod_name: str, timeout: int = 30) -> str:
        """Wait until the pod gets an IP address."""
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        
        while loop.time() - start_time < timeout:
            try:
                pod = await loop.run_in_executor(None, self._core_api.read_namespaced_pod, pod_name, self.namespace)
                if pod.status and pod.status.pod_ip:
                    return pod.status.pod_ip
            except Exception:
                pass
            await asyncio.sleep(1)
            
        raise TimeoutError(f"Pod {pod_name} did not get an IP within {timeout}s.")

    async def cleanup_sandbox(self, sandbox_id: str):
        """Terminates and cleans up the sandbox."""
        if not self._client_initialized:
            logger.info(f"Mock cleaning up K8s sandbox: {sandbox_id}")
            return
            
        logger.info(f"Terminating K8s sandbox pod: {sandbox_id}")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._core_api.delete_namespaced_pod, sandbox_id, self.namespace)
        except Exception as e:
            logger.error(f"Error terminating K8s sandbox {sandbox_id}: {e}")
