# app/sources/oci_inventory.py
"""Live OCI inventory: compute instances, block volumes, reserved public IPs.

The SDK is imported lazily inside the fetch path, so sample mode never touches it. Records carry
exactly the shape the fixture adapters produce, which is the point of the `Source` interface: the
rest of the pipeline cannot tell the difference, and nothing downstream needs to.

Failures raise `SourceError` with the operation named. The loop retries once, then degrades to
fixtures; it never fabricates records.
"""
from __future__ import annotations

import os
from typing import Any

from app.config import RunConfig
from app.sources.base import Scope, SourceError, SourceResult

TIMEOUT_S = 30
"""Every external call is bounded — the run's own caps are worthless if one list call can hang."""


def _iso(ts: Any) -> str | None:
    return ts.isoformat() if ts is not None else None


def instance_record(instance: Any) -> dict[str, Any]:
    shape_config = getattr(instance, "shape_config", None)
    return {
        "resource_id": instance.id,
        "resource_class": "compute_instance",
        "display_name": instance.display_name,
        "compartment_id": instance.compartment_id,
        "lifecycle_state": instance.lifecycle_state,
        "time_created": _iso(instance.time_created),
        "shape": instance.shape,
        "ocpus": getattr(shape_config, "ocpus", None),
        "memory_gb": getattr(shape_config, "memory_in_gbs", None),
        "tags": dict(instance.freeform_tags or {}),
    }


def volume_record(volume: Any, attached_ids: set[str]) -> dict[str, Any]:
    # `attached` is a fact about the attachments, never about the volume object itself: a volume
    # says nothing about whether anything is mounted on it.
    return {
        "resource_id": volume.id,
        "resource_class": "block_volume",
        "display_name": volume.display_name,
        "compartment_id": volume.compartment_id,
        "lifecycle_state": volume.lifecycle_state,
        "time_created": _iso(volume.time_created),
        "size_gb": volume.size_in_gbs,
        "attached": volume.id in attached_ids,
        "tags": dict(volume.freeform_tags or {}),
    }


def public_ip_record(ip: Any) -> dict[str, Any]:
    return {
        "resource_id": ip.id,
        "resource_class": "reserved_public_ip",
        "display_name": ip.display_name or getattr(ip, "ip_address", None) or ip.id,
        "compartment_id": ip.compartment_id,
        "lifecycle_state": ip.lifecycle_state,
        "time_created": _iso(ip.time_created),
        "attached": bool(getattr(ip, "assigned_entity_id", None)),
        "tags": dict(ip.freeform_tags or {}),
    }


def resolve_compartments(scope: Scope, config: RunConfig) -> list[str]:
    """Request scope wins, then config, then the environment. Guessing a compartment would audit
    the wrong tenancy slice silently, so an empty answer is an error that names the variable."""
    compartments = list(scope.compartment_ids or config.compartment_ids)
    if not compartments and os.environ.get("OCI_COMPARTMENT_ID"):
        compartments = [os.environ["OCI_COMPARTMENT_ID"]]
    if not compartments:
        raise SourceError("no compartment configured: pass scope.compartment_ids in the request "
                          "or set OCI_COMPARTMENT_ID")
    return compartments


def load_sdk_config() -> dict[str, Any]:
    """Read and validate the SDK config file. Credentials come from the environment-indirected
    file only — never from the request, never hardcoded."""
    import oci
    path = os.environ.get("OCI_CONFIG_FILE", "~/.oci/config")
    profile = os.environ.get("OCI_PROFILE", "DEFAULT")
    try:
        sdk = oci.config.from_file(path, profile)
        oci.config.validate_config(sdk)
    except Exception as exc:                          # noqa: BLE001 - reported, never retried blind
        raise SourceError(f"OCI credentials unavailable ({path} [{profile}]): {exc}") from exc
    region = os.environ.get("OCI_REGION")
    if region:
        sdk["region"] = region
    return sdk


class OCIInventorySource:
    name = "inventory"

    def __init__(self, config: RunConfig) -> None:
        self.config = config

    def fetch(self, scope: Scope) -> SourceResult:
        compartments = resolve_compartments(scope, self.config)
        sdk = load_sdk_config()
        import oci
        from oci.core import BlockstorageClient, ComputeClient, VirtualNetworkClient
        compute = ComputeClient(sdk, timeout=TIMEOUT_S)
        blockstorage = BlockstorageClient(sdk, timeout=TIMEOUT_S)
        network = VirtualNetworkClient(sdk, timeout=TIMEOUT_S)

        records: list[dict[str, Any]] = []
        for compartment_id in compartments:
            instances = self._list(compute.list_instances, compartment_id=compartment_id,
                                   retry_strategy=oci.retry.NoneRetryStrategy())
            records.extend(instance_record(instance) for instance in instances)

            attachments = self._list(compute.list_volume_attachments,
                                     compartment_id=compartment_id,
                                     retry_strategy=oci.retry.NoneRetryStrategy())
            attached_ids = {attachment.volume_id for attachment in attachments
                            if attachment.lifecycle_state in ("ATTACHED", "ATTACHING")}
            volumes = self._list(blockstorage.list_volumes, compartment_id=compartment_id,
                                 retry_strategy=oci.retry.NoneRetryStrategy())
            records.extend(volume_record(volume, attached_ids) for volume in volumes)

            reserved = self._list(network.list_public_ips, compartment_id=compartment_id,
                                  scope="REGION", retry_strategy=oci.retry.NoneRetryStrategy())
            records.extend(public_ip_record(ip) for ip in reserved
                           if ip.lifecycle_state != "TERMINATED")

        if scope.resource_types:
            records = [record for record in records
                       if record["resource_class"] in scope.resource_types]
        return SourceResult(source=self.name, backend="live", records=records)

    @staticmethod
    def _list(operation, **kwargs):
        """One paginated list call. Pagination is the SDK's; the timeout and the error naming are
        ours, so a failure says which operation failed instead of surfacing a raw SDK trace."""
        import oci
        try:
            return oci.pagination.list_call_get_all_results(operation, **kwargs).data
        except SourceError:
            raise
        except Exception as exc:                      # noqa: BLE001 - named, then degraded upstream
            raise SourceError(f"{operation.__name__} failed: {exc}") from exc
