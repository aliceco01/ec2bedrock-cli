"""Inference profile schema and bundled defaults for ec2bedrock-cli.

A *profile* captures the hardware, runtime, and budget assumptions for a
particular model deployment.  Profiles are the offline, boto3-free input to
the cost arithmetic in :mod:`ec2bedrock.cost._ec2cli`.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


class ProfileError(ValueError):
    """Raised when a profile dict cannot be validated."""


@dataclass(frozen=True)
class Profile:
    """Frozen inference-profile record.

    Attributes:
        instance_type: EC2 instance type (e.g. ``"g6e.xlarge"``).
        gpu: GPU model string (e.g. ``"l40s-48gb"``).
        runtime: Serving runtime (e.g. ``"vllm"``).
        quantization: Quantisation scheme (e.g. ``"awq"``).
        hourly_usd: On-demand hourly rate in USD.
        storage_gb: EBS volume size in GiB.
        performance: Optional parallelism / throughput guidance.
        lifecycle: Optional warmup / idle / stop-mode settings.
        budgets: Optional cost-budget thresholds.
    """

    instance_type: str
    gpu: str
    runtime: str
    quantization: str
    hourly_usd: float
    storage_gb: int
    performance: dict | None = None
    lifecycle: dict | None = None
    budgets: dict | None = None

    _required_fields = frozenset(
        {
            "instance_type",
            "gpu",
            "runtime",
            "quantization",
            "hourly_usd",
            "storage_gb",
        }
    )

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        """Build a :class:`Profile` from a plain dict, validating keys."""
        if not isinstance(d, dict):
            raise ProfileError("expected a dict, got " + type(d).__name__)

        missing = cls._required_fields - set(d.keys())
        if missing:
            raise ProfileError("missing required field(s): " + ", ".join(sorted(missing)))

        unknown = set(d.keys()) - {f.name for f in fields(cls)}
        if unknown:
            raise ProfileError("unknown field(s): " + ", ".join(sorted(unknown)))

        return cls(**d)

    def to_dict(self) -> dict:
        """Round-trip back to a plain JSON-able dict."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


DEFAULT_PROFILES: dict[str, Profile] = {
    "qwen27b-awq-l40s": Profile(
        instance_type="g6e.xlarge",
        gpu="l40s-48gb",
        runtime="vllm",
        quantization="awq",
        hourly_usd=1.861,
        storage_gb=200,
        performance={
            "comfortable_parallel_requests": "4-8",
            "aggressive_parallel_requests": "8-16",
            "expected_aggregate_tps": "80-180",
        },
        lifecycle={
            "warmup_budget_minutes": 8,
            "idle_timeout_minutes": 15,
            "stop_mode": "hibernate",
        },
        budgets={
            "warn_session_usd": 3,
            "warn_daily_usd": 25,
            "warn_monthly_usd": 500,
        },
    ),
}

__all__ = ["Profile", "ProfileError", "DEFAULT_PROFILES"]
