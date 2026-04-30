"""Shared enums for pykrairport."""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    """Airport API provider."""

    KAC = "kac"
    IIAC = "iiac"


class Direction(StrEnum):
    """Flight direction."""

    ARRIVAL = "arrival"
    DEPARTURE = "departure"
