"""Tests for the inference Profile schema and bundled defaults."""

from __future__ import annotations

import pytest

from ec2bedrock.cost.profiles import DEFAULT_PROFILES, Profile, ProfileError

# --- DEFAULT_PROFILES contents -------------------------------------------


def test_default_profile_hourly_usd() -> None:
    p = DEFAULT_PROFILES["qwen27b-awq-l40s"]
    assert p.hourly_usd == 1.861


def test_default_profile_instance_type() -> None:
    p = DEFAULT_PROFILES["qwen27b-awq-l40s"]
    assert p.instance_type == "g6e.xlarge"


def test_default_profile_storage_gb() -> None:
    p = DEFAULT_PROFILES["qwen27b-awq-l40s"]
    assert p.storage_gb == 200


# --- round-trip ----------------------------------------------------------


def test_to_dict_round_trip() -> None:
    p = DEFAULT_PROFILES["qwen27b-awq-l40s"]
    assert Profile.from_dict(p.to_dict()) == p


# --- validation errors ---------------------------------------------------


def test_from_dict_unknown_key_raises_profile_error() -> None:
    with pytest.raises(ProfileError, match="unknown field"):
        Profile.from_dict(
            {
                "instance_type": "x",
                "gpu": "g",
                "runtime": "r",
                "quantization": "q",
                "hourly_usd": 1.0,
                "storage_gb": 10,
                "bogus": 1,
            }
        )


def test_from_dict_missing_required_field_raises_profile_error() -> None:
    with pytest.raises(ProfileError, match="missing required"):
        Profile.from_dict({"instance_type": "x"})
