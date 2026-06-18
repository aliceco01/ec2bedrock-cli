"""ec2-cli coupling adapter — the milestone-1 seam onto ``ec2.aws.pricing``.

Issue #1 says ec2bedrock-cli is *built on ec2-cli*. For the cost milestone the
coupling is narrow and **offline**: we reuse ec2-cli's pure, injected-rate
per-machine arithmetic (:func:`ec2.aws.pricing.estimate_cost`) and never touch a
live AWS account. boto3 is ec2-cli's optional ``[aws]`` extra and lives only in
``ec2/aws/client.py`` / ``cost.py`` behind a lazy import, so importing
``ec2.aws.pricing`` pulls **no** boto3 — milestone 1 keeps that guarantee (see
``tests/test_ec2cli_adapter.py``).

Why an adapter instead of importing :class:`ec2.aws.pricing.Estimate` directly?
The *function signature* is stable across ec2-cli releases, but the ``Estimate``
**return shape is not**:

- ec2-cli ``0.5.x`` (the released PyPI line): a single combined ``.figure``.
- ec2-cli ``0.6.x`` (issue #4, unreleased at M1): split ``.compute`` / ``.ebs``
  plus ``.total`` / ``.unknown`` properties.

ec2bedrock wants the compute/EBS breakout (issue #1 lists EBS as a distinct cost
component). This module normalises **either** ec2-cli shape into ec2bedrock's own
:class:`CostBreakdown`, so the rest of the cost domain is insulated from which
ec2-cli version happens to be installed. Because M1 always injects a *known*
hourly rate (``profile.hourly_usd``) and a known monthly EBS cost, the breakout
is always recoverable even from the ``0.5.x`` combined ``.figure``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ec2.aws.pricing import estimate_cost as _ec2_estimate_cost


@dataclass(frozen=True)
class CostBreakdown:
    """A per-machine cost split into compute + EBS, ec2-cli-version-independent.

    ``compute`` / ``ebs`` are USD figures, or ``None`` when UNKNOWN (no usable
    rate). ``0.0`` is a *known* zero (e.g. a stopped instance), distinct from
    ``None``. The semantics mirror ec2-cli 0.6.x's ``Estimate``.
    """

    compute: float | None
    ebs: float | None
    notes: tuple[str, ...] = ()

    @property
    def total(self) -> float | None:
        """Combined compute + EBS, or ``None`` when either component is UNKNOWN."""
        if self.compute is None or self.ebs is None:
            return None
        return self.compute + self.ebs

    @property
    def unknown(self) -> bool:
        """True when the total cannot be determined from the injected inputs."""
        return self.total is None


@dataclass(frozen=True)
class _OnDemandRunning:
    """Minimal instance stand-in for ec2-cli's ``estimate_cost``.

    ``estimate_cost`` only reads ``.lifecycle`` and ``.state`` (via ``getattr``
    with defaults). M1 always prices a running, on-demand machine.
    """

    lifecycle: str = "on-demand"
    state: str = "running"


def normalize_estimate(estimate: object, *, ebs_monthly: float | None) -> CostBreakdown:
    """Map an ec2-cli ``Estimate`` (any release shape) into a :class:`CostBreakdown`.

    ``ebs_monthly`` is the value that was injected into ``estimate_cost``; it lets
    us recover the compute/EBS split from ec2-cli 0.5.x's combined ``.figure``.
    """
    notes = tuple(getattr(estimate, "notes", ()) or ())

    # ec2-cli 0.6.x: explicit compute / ebs already split out.
    if hasattr(estimate, "compute") and hasattr(estimate, "ebs"):
        return CostBreakdown(
            compute=getattr(estimate, "compute"),
            ebs=getattr(estimate, "ebs"),
            notes=notes,
        )

    # ec2-cli 0.5.x: a single combined ``.figure`` (compute + EBS). We injected
    # ``ebs_monthly``, so the compute component is recoverable by subtraction.
    figure = getattr(estimate, "figure", None)
    if figure is None:
        return CostBreakdown(compute=None, ebs=ebs_monthly, notes=notes)
    ebs = ebs_monthly if ebs_monthly is not None else 0.0
    return CostBreakdown(compute=figure - ebs, ebs=ebs, notes=notes)


def per_machine_cost(
    *,
    hourly_usd: float | None,
    running_hours: float,
    ebs_monthly: float | None,
) -> CostBreakdown:
    """Offline per-machine cost = ``hourly_usd × running_hours`` compute + EBS.

    Delegates the arithmetic + UNKNOWN-degradation to ec2-cli's
    :func:`ec2.aws.pricing.estimate_cost` (rate injected, never looked up live),
    then normalises the result. ``hourly_usd``/``ebs_monthly`` may be ``None``,
    in which case the corresponding component degrades to UNKNOWN rather than
    raising — matching ec2-cli's contract.
    """
    estimate = _ec2_estimate_cost(
        _OnDemandRunning(),
        ondemand_rate=hourly_usd,
        spot_rate=None,
        running_hours=running_hours,
        ebs_monthly=ebs_monthly,
    )
    breakdown = normalize_estimate(estimate, ebs_monthly=ebs_monthly)

    # Uniform UNKNOWN across ec2-cli releases: 0.5.x degrades a missing rate to
    # ``compute=0.0`` + a note, while 0.6.x yields ``None``. ec2bedrock owns the
    # UNKNOWN call from the rate *it* injected, so the result shape is the same
    # whichever ec2-cli is installed.
    if hourly_usd is None:
        breakdown = CostBreakdown(compute=None, ebs=breakdown.ebs, notes=breakdown.notes)
    return breakdown
