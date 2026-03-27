from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_jinja_env = Environment(undefined=StrictUndefined)


def load_prompt(module: str, prompt_name: str, **kwargs) -> tuple[str, str]:
    """Load a YAML prompt, render with kwargs, return (system, user)."""
    path = _PROMPTS_DIR / module / f"{prompt_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    system_template = _jinja_env.from_string(data.get("system", ""))
    user_template = _jinja_env.from_string(data.get("user", ""))

    return system_template.render(**kwargs), user_template.render(**kwargs)
