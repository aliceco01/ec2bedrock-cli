"""Entry point for ``python -m ec2bedrock``."""

from __future__ import annotations

import sys

from ec2bedrock.cli import main

if __name__ == "__main__":
    sys.exit(main())
