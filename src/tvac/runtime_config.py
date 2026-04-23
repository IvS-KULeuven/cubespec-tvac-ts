import os

from egse.env import bool_env

EXCLUDE_AMPLIFIER_ENV_VAR = "TVAC_NO_AMPLIFIER"


def is_amplifier_excluded() -> bool:
    return bool_env(EXCLUDE_AMPLIFIER_ENV_VAR, False)


def exclude_amplifier(exclude: bool) -> None:
    os.environ[EXCLUDE_AMPLIFIER_ENV_VAR] = "1" if exclude else "0"

    if exclude:
        os.environ["GUI_EXECUTOR_ATTENTION_LABEL"] = "NO AMPLIFIER"
