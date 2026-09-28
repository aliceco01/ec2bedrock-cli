#!/usr/bin/env python3
"""Turn one benchmark run into a cost report: EC2 vs a token provider.

Reads a results directory written by run.sh (the ``vllm bench serve`` JSON
files plus the timeline logs) and prints a markdown report, also saved as
``report.md`` in that directory. Stdlib only.

The cost model matches ec2bedrock's break-even math, but with the throughput
measured instead of assumed:

* EC2 $ per 1M output tokens = hourly price / (measured output tok/s x 3600)
  x 1M, with the instance 100% busy. The input tokens are served in the same
  instance time, so they cost nothing extra.
* Provider $ for the same tokens = output price + (input/output ratio) x input
  price, per 1M output tokens.
* Break-even utilization = EC2 $ / provider $: how busy the instance must be
  on average for EC2 to cost the same. Above 1.0, EC2 cannot match the
  provider on cost at that concurrency, however the load is scheduled.

Usage: summarize.py RESULTS_DIR [--provider-input 0.15] [--provider-output 0.60]
       [--hourly USD]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

# Bedrock's on-demand list price for Qwen3 32B (USD per 1M tokens, US regions).
BEDROCK_QWEN3_32B_INPUT = 0.15
BEDROCK_QWEN3_32B_OUTPUT = 0.60

# (label, start event, end event) for the cold start, all measured in seconds.
COLD_START_PHASES = [
    ("Launch request to instance running", "launch_requested", "running"),
    ("Boot to bootstrap start", "running", "userdata_start"),
    ("Docker ready", "userdata_start", "docker_ready"),
    ("Pull the vLLM image", "docker_ready", "image_pulled"),
    ("Download the weights", "image_pulled", "model_downloaded"),
    ("Load the model and answer /health", "server_started", "server_ready"),
    ("Total: launch request to ready", "launch_requested", "server_ready"),
]
RESTART_PHASES = [
    ("Stop", "stop_requested", "stopped"),
    ("Start request to instance running", "start_requested", "running"),
    ("Running to ready (model from EBS)", "running", "server_ready"),
    ("Total: start request to ready", "start_requested", "server_ready"),
]


@dataclass(frozen=True)
class Level:
    """One concurrency level of the sweep, with its cost figures."""

    concurrency: int
    output_tps: float
    input_output_ratio: float
    median_ttft_ms: float | None
    median_tpot_ms: float | None
    failed: int
    ec2_usd_per_1m_output: float
    provider_usd_per_1m_output: float

    @property
    def break_even_utilization(self) -> float:
        return self.ec2_usd_per_1m_output / self.provider_usd_per_1m_output


def load_levels(
    results: Path, hourly_usd: float, input_price: float, output_price: float
) -> list[Level]:
    levels = []
    for path in sorted(results.glob("*.json")):
        data = json.loads(path.read_text())
        output_tps = float(data["output_throughput"])
        ratio = data["total_input_tokens"] / data["total_output_tokens"]
        levels.append(
            Level(
                concurrency=int(data["max_concurrency"]),
                output_tps=output_tps,
                input_output_ratio=ratio,
                median_ttft_ms=data.get("median_ttft_ms", data.get("p50_ttft_ms")),
                median_tpot_ms=data.get("median_tpot_ms", data.get("p50_tpot_ms")),
                failed=int(data.get("num_prompts", data["completed"])) - int(data["completed"]),
                ec2_usd_per_1m_output=hourly_usd / (output_tps * 3600) * 1_000_000,
                provider_usd_per_1m_output=output_price + ratio * input_price,
            )
        )
    return sorted(levels, key=lambda level: level.concurrency)


def read_timeline(path: Path) -> dict[str, int]:
    """``<epoch seconds> <event>`` lines; the first occurrence of an event wins."""
    events: dict[str, int] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0].isdigit():
                events.setdefault(parts[1], int(parts[0]))
    return events


def read_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return {key.strip(): value.strip() for key, value in pairs}


def _duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def _phase_rows(events: dict[str, int], phases: list[tuple[str, str, str]]) -> list[str]:
    rows = []
    for label, start, end in phases:
        if start in events and end in events:
            rows.append(f"| {label} | {_duration(events[end] - events[start])} |")
    return rows


def _ms(value: float | None, scale: float = 1.0, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value / scale:.{digits}f}"


def build_report(
    results: Path,
    input_price: float = BEDROCK_QWEN3_32B_INPUT,
    output_price: float = BEDROCK_QWEN3_32B_OUTPUT,
    hourly_usd: float | None = None,
) -> str:
    config = read_config(results / "config.env")
    hourly = hourly_usd if hourly_usd is not None else float(config.get("hourly_usd", 1.861))
    levels = load_levels(results, hourly, input_price, output_price)
    if not levels:
        raise SystemExit(f"error: no benchmark JSON files in {results}")

    lines = [
        f"# {config.get('model', 'model')} on {config.get('instance_type', 'EC2')}",
        "",
        f"vLLM image `{config.get('vllm_image', '?')}`, "
        f"{levels[0].input_output_ratio:.1f} input tokens per output token, "
        f"EC2 at ${hourly}/h, provider at ${input_price} in / ${output_price} out per 1M tokens.",
        "",
        "| Concurrency | Output tok/s | Median TTFT (s) | Median ms per output token "
        "| EC2 $ per 1M output (100% busy) | Provider $ for the same tokens "
        "| Break-even utilization |",
        "|---|---|---|---|---|---|---|",
    ]
    for lv in levels:
        failed = f" ({lv.failed} failed)" if lv.failed else ""
        lines.append(
            f"| {lv.concurrency}{failed} | {lv.output_tps:.0f} | {_ms(lv.median_ttft_ms, 1000, 2)} "
            f"| {_ms(lv.median_tpot_ms, 1, 1)} | {lv.ec2_usd_per_1m_output:.2f} "
            f"| {lv.provider_usd_per_1m_output:.2f} | {lv.break_even_utilization:.0%} |"
        )

    best = max(levels, key=lambda level: level.output_tps)
    verdict = (
        "EC2 can match the provider only if it stays at least that busy."
        if best.break_even_utilization <= 1
        else "EC2 cannot match the provider on cost at these prices, even flat out."
    )
    lines += [
        "",
        f"Peak: {best.output_tps:.0f} output tok/s at concurrency {best.concurrency}, "
        f"break-even at {best.break_even_utilization:.0%} utilization. {verdict}",
    ]

    events = read_timeline(results / "local-timeline.log") | read_timeline(results / "timeline.log")
    rows = _phase_rows(events, COLD_START_PHASES)
    if rows:
        lines += ["", "## Cold start", "", "| Phase | Time |", "|---|---|", *rows]
    rows = _phase_rows(read_timeline(results / "restart-timeline.log"), RESTART_PHASES)
    if rows:
        lines += ["", "## Stop and start", "", "| Phase | Time |", "|---|---|", *rows]

    server_log = results / "server.log"
    if server_log.exists() and server_log.read_text().strip():
        lines += ["", "## Server capacity (from the vLLM log)", "", "```text"]
        lines += [server_log.read_text().strip(), "```"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path, help="A bench/results/<run id> directory.")
    parser.add_argument("--provider-input", type=float, default=BEDROCK_QWEN3_32B_INPUT)
    parser.add_argument("--provider-output", type=float, default=BEDROCK_QWEN3_32B_OUTPUT)
    parser.add_argument("--hourly", type=float, default=None, help="Override config.env.")
    args = parser.parse_args(argv)
    report = build_report(args.results, args.provider_input, args.provider_output, args.hourly)
    (args.results / "report.md").write_text(report)
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
