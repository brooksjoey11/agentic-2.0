"""Kubernetes tool — interact with a Kubernetes cluster."""
from typing import Any

from kubernetes import client, config as k8s_config  # type: ignore[import]


def load_kube_config() -> None:
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()


def list_pods(namespace: str = "default") -> list[dict[str, Any]]:
    load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace)
    return [{"name": p.metadata.name, "status": p.status.phase} for p in pods.items]


def apply_manifest(manifest: dict[str, Any]) -> None:
    load_kube_config()
    apps_v1 = client.AppsV1Api()
    if manifest.get("kind") == "Deployment":
        apps_v1.create_namespaced_deployment(
            namespace=manifest["metadata"].get("namespace", "default"),
            body=manifest,
        )
