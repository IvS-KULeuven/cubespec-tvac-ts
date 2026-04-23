import os

NO_AMPLIFIER_ENV_VAR = "TVAC_NO_AMPLIFIER"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def no_amplifier_enabled() -> bool:
    value = os.environ.get(NO_AMPLIFIER_ENV_VAR, "")
    return value.strip().lower() in _TRUE_VALUES


def set_no_amplifier(enabled: bool) -> None:
    os.environ[NO_AMPLIFIER_ENV_VAR] = "1" if enabled else "0"
