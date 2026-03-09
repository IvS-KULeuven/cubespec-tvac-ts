"""
High-level strain-gauge logging functions.

Reads LabJack T7 and CSV configuration from the CGSE Setup, mirrors
the pattern of ``tvac.power_supply`` for heaters.
"""

import csv
import os
import datetime
import threading
import bisect
from typing import Optional

from egse.observation import building_block
from egse.setup import Setup, load_setup


# ---------------------------------------------------------------------------
# Module-level state for the active logging session
# ---------------------------------------------------------------------------
_logger = None  # LabJackT7Logger, imported lazily to avoid LJM init on import
_csv_lock = threading.Lock()
_csv_file = None
_csv_writer = None
_csv_filename = ""
_file_index = 0
_read_count = 0
_start_ts = ""

# CSV defaults (overridden by setup)
_csv_enabled = True
_save_path = "."
_base_filename = "labjack_sg_data"
_max_file_size = 5_000 * 1024

# Plot flag
_plot_enabled = True

# Plot buffers (shared with any live-plot consumer)
plot_lock = threading.Lock()
time_buffer: list[float] = []
ch_buffers: list[list[float]] = []


def _rotate_csv(headers):
    global _file_index, _csv_file, _csv_writer, _csv_filename

    if _csv_file:
        _csv_file.close()
    fname = f"{_base_filename}_{_start_ts}_{_file_index:03d}.csv"
    _csv_filename = os.path.join(_save_path, fname)
    _csv_file = open(_csv_filename, "w", newline="")
    _csv_writer = csv.writer(_csv_file)
    _csv_writer.writerow(["Timestamp"] + headers)
    _file_index += 1
    print(f"Logging to: {_csv_filename}")


def _on_stream_data(*, timestamps, readings, channel_names, device_backlog, ljm_backlog):
    global _read_count, _csv_writer, _csv_file, _csv_filename

    if _csv_enabled:
        with _csv_lock:
            if _csv_writer is None:
                _rotate_csv(channel_names)

            rows = [
                [ts.isoformat()] + list(row)
                for ts, row in zip(timestamps, readings)
            ]
            _csv_writer.writerows(rows)
            _csv_file.flush()

            _read_count += 1
            if _read_count % 10 == 0:
                print(
                    f"Read #{_read_count}: {len(timestamps)} scans | "
                    f"Device backlog: {device_backlog} | LJM backlog: {ljm_backlog}"
                )

            if os.path.getsize(_csv_filename) >= _max_file_size:
                _rotate_csv(channel_names)

    if _plot_enabled:
        t0 = _logger.stream_start_time
        new_times = [(ts - t0).total_seconds() for ts in timestamps]
        new_vals = list(zip(*readings))

        with plot_lock:
            time_buffer.extend(new_times)
            for ch_idx in range(len(channel_names)):
                ch_buffers[ch_idx].extend(new_vals[ch_idx])


@building_block
def start_sg_logging(setup: Setup = None):
    """Start strain-gauge streaming and CSV logging from the CGSE Setup.

    Reads all LabJack T7 channel, stream, and CSV parameters from
    ``setup.gse.labjack_t7``.
    """
    global _logger, _csv_enabled, _save_path, _base_filename, _max_file_size
    global _plot_enabled, _start_ts
    global _file_index, _read_count, _csv_file, _csv_writer, _csv_filename

    if _logger is not None:
        print("Strain-gauge logging is already running.")
        return

    setup = setup or load_setup()
    cfg = setup.gse.labjack_t7

    # CSV config
    _csv_enabled = cfg.csv.enabled
    _save_path = str(cfg.csv.save_path)
    _base_filename = cfg.csv.base_filename
    _max_file_size = cfg.csv.max_file_size_bytes

    if _csv_enabled:
        os.makedirs(_save_path, exist_ok=True)

    _start_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _file_index = 0
    _read_count = 0
    _csv_file = None
    _csv_writer = None
    _csv_filename = ""

    # Plot config
    _plot_enabled = cfg.plot.enabled

    # Reset plot buffers
    n_ch = len(cfg.channels)
    with plot_lock:
        time_buffer.clear()
        ch_buffers.clear()
        ch_buffers.extend([] for _ in range(n_ch))

    from tvac.labjack_t7 import LabJackT7Logger
    _logger = LabJackT7Logger.from_setup(setup)
    _logger.start_stream(callback=_on_stream_data)


@building_block
def stop_sg_logging():
    """Stop the active strain-gauge logging session."""
    global _logger, _csv_file

    if _logger is None:
        print("No strain-gauge logging session is active.")
        return

    _logger.close()
    _logger = None

    if _csv_file:
        _csv_file.close()

    print("Strain-gauge logging stopped.")


def get_sg_status() -> str:
    """Return a short status string for the current logging session."""
    if _logger is None:
        return "Not running"
    rate = _logger.actual_scan_rate
    return (
        f"Running at {rate:.1f} Hz, "
        f"{_logger.num_addresses} channels, "
        f"{_read_count} reads, "
        f"file: {_csv_filename}"
    )


def trim_plot_buffers(keep_seconds: float):
    """Remove plot-buffer samples older than *keep_seconds* from the latest."""
    with plot_lock:
        if not time_buffer:
            return
        cutoff = time_buffer[-1] - keep_seconds
        idx = bisect.bisect_left(time_buffer, cutoff)
        if idx > 0:
            del time_buffer[:idx]
            for buf in ch_buffers:
                del buf[:idx]
