#!/usr/bin/env python3
"""Compatibility entry point for the organize-dicoms command."""

from __future__ import annotations

from organize_dicoms.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
