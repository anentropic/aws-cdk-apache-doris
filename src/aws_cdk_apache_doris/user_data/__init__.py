"""User data template helpers for the Doris CDK app."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

_USER_DATA_DIR = Path(__file__).resolve().parent


def _load_template(name: str) -> str:
    return (_USER_DATA_DIR / name).read_text(encoding="utf-8")


BE_USER_DATA_TEMPLATE = _load_template("be_user_data.sh")
FE_USER_DATA_TEMPLATE = _load_template("fe_user_data.sh")


def render_user_data(template: str, replacements: Mapping[str, Any]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"__{key}__", str(value))
    return rendered
