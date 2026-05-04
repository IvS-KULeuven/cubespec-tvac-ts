import argparse
import os
import shlex
import sys
from pathlib import Path

from egse.setup import load_setup
from executor import ExternalCommand
import gui_executor.client as client

from tvac.runtime_config import exclude_amplifier

HERE = Path(__file__).parent.resolve()

UI_TAB_ORDER = ["heaters", "piezos", "strain_gauges", "observations"]


def _wait_for_ready(self, timeout: float = 60.0):
    return self._client.wait_for_ready(timeout=timeout)


def _resolve_cmd_log_dir() -> str:
    cmd_log = os.environ.get("CUBESPEC_LOG_FILE_LOCATION")
    if cmd_log is None or not os.access(cmd_log, os.W_OK):
        cmd_log = str(Path("~").expanduser())
    return cmd_log


def _parse_tvac_ui_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--no-amplifier",
        action="store_true",
        help="Run the piezo UI without the external amplifier in the signal chain.",
    )
    return parser.parse_known_args(argv)


def tvac_ui():
    client.MyClient.wait_for_ready = _wait_for_ready  # type: ignore[assignment]
    args, gui_executor_args = _parse_tvac_ui_args(sys.argv[1:])
    exclude_amplifier(args.no_amplifier)

    logo_path = HERE / "icons/dashboard.svg"
    cmd_log = _resolve_cmd_log_dir()
    passthrough_args = shlex.join(gui_executor_args)
    passthrough = f" {passthrough_args}" if passthrough_args else ""

    setup = load_setup()

    cmd_str = "gui-executor --verbose "

    # Incl. tabs depending on what is present in the setup (see #99)

    if "power_supply" in setup.gse:
        cmd_str += " --module-path tvac.tasks.tvac.heaters"
    if "wave_generators" in setup.gse:
        cmd_str += " --module-path tvac.tasks.tvac.piezos"
    if "labjack_t7" in setup.gse:
        cmd_str += " --module-path tvac.tasks.tvac.strain_gauges"

    cmd_str += (
        f" --module-path tvac.tasks.tvac.observations"
        f" --kernel-name cubespec-tvac-ts --single"
        f" --logo {logo_path}"
        f" --cmd-log {cmd_log}"
        f" --app-name 'TVAC GUI' "
        f" {passthrough}"
    )

    cmd = ExternalCommand(
        cmd_str,
        asynchronous=True,
    )
    cmd.start()
