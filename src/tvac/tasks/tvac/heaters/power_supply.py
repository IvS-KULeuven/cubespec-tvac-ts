from pathlib import Path

from gui_executor.exec import exec_ui
from gui_executor.utypes import Callback

from tvac.heaters import config_psu, switch_off_psu
from tvac.tasks.tvac.heaters import heaters, dissipation_modes

UI_MODULE_DISPLAY_NAME = "1 - Power supplies"
HERE = Path(__file__).parent.parent.resolve()
ICON_PATH = HERE / "icons/"


@exec_ui(display_name="Configuration & switch-on", use_kernel=True)
def switch_on_heater(
    heater: Callback(heaters, name="Heater") = None,
    dissipation: Callback(dissipation_modes, name="Heat dissipation") = None,
) -> None:
    """Configures and switches on the Power Supply Unit for the given heater in the given heat dissipation mode.

    Args:
        heater: Name of the heater.
        dissipation: Heat dissipation mode.  The corresponding resistance, power, and maximum power are read from the
                     setup.
    """

    # start_observation(f"Configure + switch on heater {heater}")

    config_psu(heater_name=heater, dissipation=dissipation)

    # end_observation()


@exec_ui(display_name="Switch-off", use_kernel=True)
def switch_off_heater(heater: Callback(heaters, name="Heater") = None) -> None:
    """Switches off the Power Supply Unit for the given heater.

    Args:
        heater: Name of the heater.
    """

    # start_observation(f"Switch off heater {heater}")

    switch_off_psu(heater_name=heater)

    # end_observation()
