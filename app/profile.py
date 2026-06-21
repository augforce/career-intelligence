from __future__ import annotations
import yaml
from dataclasses import dataclass
from app.config import PROFILE_PATH


@dataclass
class Profile:
    raw: dict

    @property
    def version(self) -> int:
        return self.raw["profile_version"]

    @property
    def weights(self) -> dict:
        return self.raw["weights"]

    @property
    def signal_saturation(self) -> int:
        return self.raw["signal_saturation"]

    @property
    def favorable_signals(self) -> dict:
        return self.raw["favorable_signals"]

    @property
    def penalty_signals(self) -> dict:
        return self.raw["penalty_signals"]

    @property
    def gates(self) -> dict:
        return self.raw["gates"]

    @property
    def remote_fit(self) -> dict:
        return self.raw["remote_fit"]

    @property
    def arrangement_keywords(self) -> dict:
        return self.raw["arrangement_keywords"]

    @property
    def evidence_facets(self) -> dict:
        return self.raw["evidence_facets"]

    @property
    def work_mix_map(self) -> dict:
        return self.raw["work_mix_map"]

    @property
    def bands(self) -> dict:
        return self.raw["bands"]

    @property
    def location_defaults(self) -> dict:
        return self.raw["location_defaults"]


def load_profile(path=None) -> Profile:
    path = path or PROFILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert sum(data["weights"].values()) == 100, "weights must sum to 100"
    return Profile(raw=data)
