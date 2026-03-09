from pathlib import Path

from egse.observation import start_observation, end_observation
from egse.setup import load_setup
from gui_executor.exec import exec_ui

from tvac.strain_gauge import start_sg_logging, stop_sg_logging, get_sg_status

UI_MODULE_DISPLAY_NAME = "1 - Strain Gauges"
HERE = Path(__file__).parent.parent.resolve()
ICON_PATH = HERE / "icons/"


@exec_ui(display_name="Start logging", use_kernel=True)
def start_logging() -> None:
    """Start strain-gauge streaming and CSV logging.

    All parameters (channels, scan rate, voltage ranges, resolution indices,
    CSV path/enabled, plot enabled) are read from the active CGSE Setup
    (``setup.gse.labjack_t7``).
    """

    start_observation("Start strain-gauge logging")
    try:
        setup = load_setup()
        start_sg_logging(setup=setup)

        if setup.gse.labjack_t7.plot.enabled:
            from tvac.strain_gauge_plot import open_live_plot
            open_live_plot(setup=setup)

    except Exception as e:
        print(f"Failed to start strain-gauge logging: {e}")
    end_observation()


@exec_ui(display_name="Stop logging", use_kernel=True)
def stop_logging() -> None:
    """Stop the active strain-gauge logging session."""

    start_observation("Stop strain-gauge logging")
    try:
        stop_sg_logging()
    except Exception as e:
        print(f"Failed to stop strain-gauge logging: {e}")
    end_observation()


@exec_ui(display_name="Status", use_kernel=True)
def status() -> None:
    """Print the current strain-gauge logging status."""

    print(get_sg_status())
