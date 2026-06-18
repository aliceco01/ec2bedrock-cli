"""TOML config loader for ec2bedrock-cli.

Bundles defaults from :mod:`ec2bedrock.cost.profiles` and
:mod:`ec2bedrock.cost.rates`, optionally overridden by a user-writable
``config.toml``.  Pure stdlib — no boto3.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ec2bedrock.cost.profiles import DEFAULT_PROFILES, Profile, ProfileError
from ec2bedrock.cost.rates import (
    DEFAULT_PROVIDER_INPUT_USD_PER_1M,
    DEFAULT_PROVIDER_OUTPUT_USD_PER_1M,
)

DEFAULT_CONFIG_PATH = Path.home() / ".ec2bedrock" / "config.toml"


@dataclass(frozen=True)
class Config:
    """Loaded configuration."""

    profiles: dict[str, Profile]
    provider_input_usd_per_1m: float
    provider_output_usd_per_1m: float


def load_config(path: Path | None = None) -> Config:
    """Load configuration from *path* (or the default location).

    When the file does not exist, returns a :class:`Config` built from the
    bundled defaults.  When it exists, the TOML may override provider prices
    and / or profiles.
    """
    resolved = path if path is not None else DEFAULT_CONFIG_PATH

    profiles: dict[str, Profile] = dict(DEFAULT_PROFILES)
    provider_input = DEFAULT_PROVIDER_INPUT_USD_PER_1M
    provider_output = DEFAULT_PROVIDER_OUTPUT_USD_PER_1M

    if not resolved.exists():
        return Config(
            profiles=profiles,
            provider_input_usd_per_1m=provider_input,
            provider_output_usd_per_1m=provider_output,
        )

    with open(resolved, "rb") as f:
        data = tomllib.load(f)

    provider_table = data.get("provider", {})
    if "input_usd_per_1m" in provider_table:
        provider_input = float(provider_table["input_usd_per_1m"])
    if "output_usd_per_1m" in provider_table:
        provider_output = float(provider_table["output_usd_per_1m"])

    raw_profiles = data.get("profiles", {})
    for name, table in raw_profiles.items():
        profiles[name] = Profile.from_dict(table)

    return Config(
        profiles=profiles,
        provider_input_usd_per_1m=provider_input,
        provider_output_usd_per_1m=provider_output,
    )


def get_profile(config: Config, name: str) -> Profile:
    """Return the named profile from *config*, raising :class:`ProfileError` if absent."""
    try:
        return config.profiles[name]
    except KeyError:
        raise ProfileError(f"unknown profile: {name!r}") from None
