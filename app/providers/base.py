from __future__ import annotations
from typing import Protocol
from app.models import NormalizedJob


class JobProvider(Protocol):
    def fetch(self) -> list[NormalizedJob]: ...
