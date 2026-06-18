"""Tests for ec2bedrock.cost.config — TOML config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from ec2bedrock.cost.config import get_profile, load_config
from ec2bedrock.cost.profiles import ProfileError


class TestLoadConfigDefaults:
    """load_config with a missing file returns bundled defaults."""

    def test_missing_file_returns_defaults(self) -> None:
        config = load_config(Path("/nonexistent/config.toml"))
        assert "qwen27b-awq-l40s" in config.profiles
        assert config.provider_input_usd_per_1m == 0.58
        assert config.provider_output_usd_per_1m == 3.01


class TestLoadConfigOverrides:
    """load_config with a TOML file can override provider prices and profiles."""

    def test_provider_and_profile_overrides(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text("""\
[provider]
input_usd_per_1m = 0.50

[profiles.qwen27b-awq-l40s]
instance_type = "g6e.xlarge"
gpu = "l40s-48gb"
runtime = "vllm"
quantization = "awq"
hourly_usd = 2.0
storage_gb = 200

[profiles.tiny]
instance_type = "t3.micro"
gpu = "none"
runtime = "llama-cpp"
quantization = "q4"
hourly_usd = 0.05
storage_gb = 50
""")
        config = load_config(cfg)
        assert config.provider_input_usd_per_1m == 0.50
        assert config.profiles["qwen27b-awq-l40s"].hourly_usd == 2.0
        assert "tiny" in config.profiles

    def test_unknown_field_raises_profile_error(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text("""\
[profiles.bad]
instance_type = "x"
gpu = "g"
runtime = "r"
quantization = "q"
hourly_usd = 1.0
storage_gb = 10
bogus = 1
""")
        with pytest.raises(ProfileError, match="unknown field"):
            load_config(cfg)


class TestGetProfile:
    def test_unknown_profile_raises_profile_error(self) -> None:
        config = load_config(Path("/nonexistent/config.toml"))
        with pytest.raises(ProfileError, match="unknown profile"):
            get_profile(config, "nope")
