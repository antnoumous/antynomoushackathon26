from __future__ import annotations

from typing import Any

from app.models import IaCDeclaration, MetricSeries, PolicyRule, Resource


def stats_from_series(series: MetricSeries) -> dict[str, Any]:
    values = [p.value for p in series.points]
    if not values:
        return {"n": 0, "mean": 0.0, "peak": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0,
                "peak_timestamps": [], "coverage_ratio": 0.0, "sufficient": False}
    ordered = sorted(values)

    def percentile(q: float) -> float:
        return ordered[min(len(ordered) - 1, int(q * len(ordered)))]

    peak = max(values)
    return {
        "n": len(values),
        "mean": round(sum(values) / len(values), 3),
        "peak": peak,
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "peak_timestamps": [p.ts.isoformat() for p in series.points if p.value == peak][:3],
        "coverage_ratio": round(series.coverage_hours / series.lookback_hours, 3),
        "sufficient": series.sufficient,
    }


def monthly_cost(resource: Resource, pricing: dict[str, Any]) -> float:
    hours = pricing["hours_per_month"]
    if resource.resource_class == "compute_instance":
        rates = pricing["shapes"][resource.shape]          # KeyError on an unknown shape: fail loudly
        return round(resource.ocpus * hours * rates["ocpu_hour"]
                     + resource.memory_gb * hours * rates["gb_hour"], 2)
    if resource.resource_class == "block_volume":
        return round((resource.size_gb or 0.0) * pricing["block_volume_gb_month"], 2)
    if resource.resource_class == "reserved_public_ip":
        return round(pricing["reserved_public_ip_hour"] * hours, 2)
    raise KeyError(resource.resource_class)


def savings_upper_bound(resource: Resource, pricing: dict[str, Any]) -> float:
    """An upper bound, never a promise: what the resource costs if the finding is actionable."""
    return monthly_cost(resource, pricing)


def match_iac(resource: Resource, declarations: list[IaCDeclaration]) -> tuple[str | None, IaCDeclaration | None]:
    declared = resource.tags.get("iac_address")
    if declared:
        for item in declarations:
            if item.address == declared:
                return "tag", item
    for item in declarations:
        if item.declared_name == resource.display_name:
            return "name", item
    normalised = resource.display_name.lower().replace("-", "_").replace(" ", "_")
    for item in declarations:
        if item.declared_name.lower().replace("-", "_").replace(" ", "_") == normalised:
            return "normalised", item
    return None, None


def _matches(resource: Resource, stats: dict[str, Any], attached: bool | None,
             absent_from_iac: bool, when: dict[str, Any]) -> bool:
    if "resource_class" in when and when["resource_class"] != resource.resource_class:
        return False
    if "compute_instance" in when and when["compute_instance"] != (resource.resource_class == "compute_instance"):
        return False
    if "attached" in when and when["attached"] != attached:
        return False
    if "absent_from_iac" in when and when["absent_from_iac"] != absent_from_iac:
        return False
    if "min_coverage_ratio" in when and stats["coverage_ratio"] < when["min_coverage_ratio"]:
        return False
    if "mean_cpu_lt" in when and not stats["mean"] < when["mean_cpu_lt"]:
        return False
    if "peak_cpu_lt" in when and not stats["peak"] < when["peak_cpu_lt"]:
        return False
    if "peak_cpu_gte" in when and not stats["peak"] >= when["peak_cpu_gte"]:
        return False
    return True


def qualifying_rules(resource: Resource, stats: dict[str, Any], attached: bool | None,
                     absent_from_iac: bool, rules: list[PolicyRule]) -> list[PolicyRule]:
    return [r for r in rules if _matches(resource, stats, attached, absent_from_iac, r.when)]
