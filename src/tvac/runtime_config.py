import os

from egse.env import bool_env

EXCLUDE_AMPLIFIER_ENV_VAR = "0"


def is_amplifier_excluded() -> bool:
    return bool_env(EXCLUDE_AMPLIFIER_ENV_VAR, False)


def exclude_amplifier(exclude: bool) -> None:
    os.environ[EXCLUDE_AMPLIFIER_ENV_VAR] = "1" if exclude else "0"

    if exclude:
        os.environ.pop("GUI_EXECUTOR_ATTENTION_LABEL", None)
    else:
        os.environ["GUI_EXECUTOR_ATTENTION_LABEL"] = "AMPLIFIER IN USE"
