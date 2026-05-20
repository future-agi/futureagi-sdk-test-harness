from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Contract:
    version: str
    name: str
    suites: list[dict[str, Any]]


def default_contract_path() -> Path:
    return Path(__file__).resolve().parents[2] / "CONTRACT.yaml"


def load_contract(path: str | Path | None = None) -> Contract:
    contract_path = Path(path) if path else default_contract_path()
    with contract_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Contract must be a mapping: {contract_path}")

    suites = raw.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("Contract must define at least one suite")

    return Contract(
        version=str(raw.get("version", "0")),
        name=str(raw.get("name", contract_path.stem)),
        suites=suites,
    )
