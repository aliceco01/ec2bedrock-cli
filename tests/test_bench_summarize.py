"""Tests for bench/summarize.py, the EC2 vs token-provider cost report.

The benchmark itself needs a GPU instance; the report is plain arithmetic over
its output files, so it is tested here with a synthetic run.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "bench" / "summarize.py"
_spec = importlib.util.spec_from_file_location("bench_summarize", _PATH)
summarize = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = summarize  # dataclasses look the module up by name
_spec.loader.exec_module(summarize)


def _level(concurrency: int, output_tps: float, prompts: int, completed: int) -> dict:
    return {
        "max_concurrency": concurrency,
        "num_prompts": prompts,
        "completed": completed,
        "output_throughput": output_tps,
        "total_input_tokens": 4096 * completed,
        "total_output_tokens": 512 * completed,
        "median_ttft_ms": 850.0,
        "median_tpot_ms": 42.5,
    }


@pytest.fixture
def run(tmp_path: Path) -> Path:
    (tmp_path / "in4096_out512_c1.json").write_text(json.dumps(_level(1, 30.0, 20, 20)))
    (tmp_path / "in4096_out512_c16.json").write_text(json.dumps(_level(16, 300.0, 128, 127)))
    (tmp_path / "local-timeline.log").write_text("1000 launch_requested\n1020 running\n")
    (tmp_path / "timeline.log").write_text(
        "1050 userdata_start\n1060 docker_ready\n1300 image_pulled\n1500 model_downloaded\n"
        "1505 server_started\n1700 server_ready\n1705 sweep_start\n"
    )
    (tmp_path / "restart-timeline.log").write_text(
        "5000 stop_requested\n5060 stopped\n5062 start_requested\n5100 running\n5280 server_ready\n"
    )
    (tmp_path / "config.env").write_text(
        "instance_type=g6e.xlarge\nmodel=Qwen/Qwen3-32B-AWQ\nvllm_image=vllm/vllm-openai:v0.30.0\n"
        "hourly_usd=1.861\n"
    )
    return tmp_path


def test_cost_figures_per_level(run: Path) -> None:
    levels = summarize.load_levels(run, 1.861, 0.15, 0.60)
    assert [lv.concurrency for lv in levels] == [1, 16]
    busy = levels[1]
    assert busy.input_output_ratio == pytest.approx(8.0)
    assert busy.ec2_usd_per_1m_output == pytest.approx(1.861 / (300 * 3600) * 1e6)  # ~1.72
    assert busy.provider_usd_per_1m_output == pytest.approx(0.60 + 8 * 0.15)  # 1.80
    assert busy.break_even_utilization == pytest.approx(1.7231 / 1.80, abs=1e-3)
    assert busy.failed == 1
    # One request at a time: ten times the cost per token, far past break-even.
    assert levels[0].break_even_utilization > 1


def test_report(run: Path) -> None:
    report = summarize.build_report(run)
    assert report.startswith("# Qwen/Qwen3-32B-AWQ on g6e.xlarge")
    assert "| 16 (1 failed) | 300 | 0.85 | 42.5 | 1.72 | 1.80 | 96% |" in report
    assert "Peak: 300 output tok/s at concurrency 16, break-even at 96% utilization." in report
    assert "| Total: launch request to ready | 11m 40s |" in report
    assert "| Download the weights | 3m 20s |" in report
    assert "| Running to ready (model from EBS) | 3m 00s |" in report


def test_main_writes_report_md(run: Path, capsys) -> None:
    assert summarize.main([str(run), "--provider-input", "0.58", "--provider-output", "3.01"]) == 0
    out = capsys.readouterr().out
    assert (run / "report.md").read_text() == out
    # At the CLI's default provider prices, a busy instance beats the provider.
    assert "break-even at 23% utilization. EC2 can match the provider only if" in out


def test_empty_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no benchmark JSON files"):
        summarize.build_report(tmp_path)
