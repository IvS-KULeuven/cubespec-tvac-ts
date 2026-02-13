from typing import List

UI_TAB_DISPLAY_MODE = "Heaters"


def heaters() -> List[str]:
    """Names of the heaters.  Each of them has a dedicated Power Supply Unit."""

    return [
        "HFGS",
        "HDET",
        "HDEL",
        "HPCU",
        "HADC",
        "HACT",
        "HSAG",
        "HAV1",
        "HAV2",
        "HFSS",
    ]


def dissipation_modes() -> List[str]:
    """Heat dissipation modes of the heaters."""

    return ["HOT case (science observations)", "COLD case (safe dissipation)"]
