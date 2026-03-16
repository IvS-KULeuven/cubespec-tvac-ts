import numpy as np
import time
from egse.arbitrary_wave_generator.aim_tti import (
    WaveformShape,
    OutputWaveformType,
    Output,
    SweepType,
    SweepMode,
    Sweep,
)
from egse.arbitrary_wave_generator.aim_tti.tgf4000 import Tgf4000Interface
from egse.observation import building_block
from egse.setup import load_setup, Setup


class ArbConfig:
    def __init__(
        self, name: str, frequency: float, output_load: float | str, signal: np.ndarray
    ):
        """Initialisation of a configuration for an arbitrary waveform for an Aim-TTi TGF4000 device.

        Args:
            name (str): User=specified waveform name.
            frequency (float): Waveform frequency [Hz].
            output_load (float| str): Output load, ranging from 1 to 100000 Ohm, or "OPEN".
            signal (np.ndarray): Voltage profile to use for the waveform [V].  The amplitude and DC offset are derived
                                 from this array.
        """

        self._name = name

        self._frequency = frequency  # Frequency [Hz]
        # noinspection PyUnresolvedReferences
        self._amplitude = float(np.max(signal) - np.min(signal))  # Amplitude [V]
        # noinspection PyUnresolvedReferences
        self._dc_offset = float(
            (np.max(signal) - np.min(signal)) / 2.0
        )  # DC offset [V]
        self._output_load = output_load  # Output load [Ω]

        self._signal = signal

    @property
    def name(self) -> str:
        """Returns the name of the waveform.

        Returns:
            Name of the waveform.
        """

        return self._name

    @property
    def frequency(self) -> float:
        """Returns the frequency of the waveform.

        Returns:
            Frequency of the waveform [Hz].
        """

        return self._frequency

    @property
    def amplitude(self) -> float:
        """Returns the amplitude of the waveform.

        Returns:
            Amplitude of the waveform [Vpp].
        """

        return self._amplitude

    @property
    def dc_offset(self) -> float:
        """Returns the DC offset of the waveform.

        Returns:
            DC offset of the waveform [V].
        """

        return self._dc_offset

    @property
    def output_load(self) -> float | str:
        """Returns the output load of the waveform.

        Returns:
            Output load of the waveform, ranging from 1 to 100000 Ohm, or "OPEN".
        """

        return self._output_load

    @property
    def signal(self) -> np.ndarray:
        """Returns the original voltage profile that will be fed to an Aim-TTi TGF4000 device.

        Returns:
            Original voltage profile that will be fed to an Aim-TTi TGF4000 device.
        """

        return self._signal

    def get_signal_as_hex(self) -> str:
        """Returns the string that must be passed to the ARB1/2/3/4 command to load an arbitrary waveform.

        Returns:
            Data consisting of two bytes per point with no characters between bytes or points. The point data is sent
            high byte first. The data block has a header which consists of the # character followed by several ascii
            coded numeric characters. The first of these defines the number of ascii characters to follow and these
            following characters define the length of the binary data in bytes. The instrument will wait for data
            indefinitely If less data is sent. If more data is sent the extra is processed by the command parser which
            results in a command error.
        """

        def int16_to_hex(value):
            return int(value).to_bytes(2, byteorder="big", signed=True).hex().upper()

        # Map to signed 16-bit integer (in the range [-32767, 32767])

        min_signal, max_signal = np.min(self.signal), np.max(self.signal)
        signal16 = (self.signal - min_signal) / (max_signal - min_signal) * (
            65535 - 1
        ) - (65535 // 2)
        signal16 = signal16.astype(np.int16)

        array = []
        for number in signal16:
            hex_number = int16_to_hex(number)

            u = np.uint16(int(hex_number, 16))
            s = u.view(np.int16)
            array.append(int(s))

        byte_string = bytes()

        for number in array:
            byte_string += number.to_bytes(length=2, byteorder="big", signed=True)

        byte_array = byte_string.decode(encoding="latin1", errors="ignore")
        str_num_bytes = str(len(byte_array))  # Number of points in the waveform
        len_num_bytes = len(
            str_num_bytes
        )  # Number of digits needed to express the number of points in the waveform
        arb = rf"#{len_num_bytes:1d}{str_num_bytes}{byte_array}"

        return arb


@building_block
def load_voltage_profile(profile: str, setup: Setup = None) -> None:
    """Configures the wave generators to send voltage profiles to the piezo actuators.

    Args:
        profile (str): Voltage profile.
        setup (Setup): Setup from which to extract the information from the wave generators.
    """

    setup = setup or load_setup()

    v1_config, v2_config, v3_config, frequency = extract_awg_config_from_setup(
        profile, setup=setup
    )

    awg1: Tgf4000Interface = setup.gse.wave_generators.awg1.device
    awg2: Tgf4000Interface = setup.gse.wave_generators.awg2.device

    for awg, channel, config in zip(
        (awg1, awg1, awg2), (1, 2, 1), (v1_config, v2_config, v3_config)
    ):
        # Configure the current channel for the current wave generator, based on the current configuration information

        output_waveform_type = OutputWaveformType(f"ARB{channel}")

        awg.set_channel(channel)  # Select the channel (1/2)
        awg.set_waveform_shape(WaveformShape.ARB)  # Select "ARB" waveform
        awg.set_amplitude(config.amplitude)  # Amplitude [Vpp]
        awg.set_output_load(config.output_load)  # Output load
        awg.set_dc_offset(config.dc_offset)  # DC offset
        awg.set_frequency(frequency)  # Frequency [Hz]
        awg.define_arb_waveform(output_waveform_type, config.name, Output.OFF)
        awg.load_arb1_ascii(
            config.get_signal_as_hex()
        ) if channel == 1 else awg.load_arb2_ascii(
            config.get_signal_as_hex()
        )  # Waveform shape
        time.sleep(2)
        awg.set_arb_waveform(output_waveform_type)
        awg.set_output(Output.ON)  # Switch on


def extract_awg_config_from_setup(profile: str, setup: Setup = None):
    """Extracts the configuration of the wave generators from the setup.

    Args:
        profile (str): Voltage profile.
        setup (Setup): Setup from which to extract the information from the wave generators.

    Returns:
        Three dictionaries with the waveform configuration for the three piezo actuators and the corresponding
        frequency [Hz].
    """

    setup = setup or load_setup()
    calibration = setup.gse.wave_generators.calibration

    # noinspection PyUnresolvedReferences
    factor = calibration.factor
    # noinspection PyUnresolvedReferences
    output_load = calibration.output_load
    # noinspection PyUnresolvedReferences
    profile = calibration.profiles[profile]
    frequency = profile["frequency"]

    v1_config = ArbConfig(
        name="V1_V",
        frequency=frequency,
        output_load=output_load,
        signal=profile["V1_V"] * factor,
    )
    v2_config = ArbConfig(
        name="V2_V",
        frequency=frequency,
        output_load=output_load,
        signal=profile["V2_V"] * factor,
    )
    v3_config = ArbConfig(
        name="V3_V",
        frequency=frequency,
        output_load=output_load,
        signal=profile["V3_V"] * factor,
    )

    return v1_config, v2_config, v3_config, frequency


@building_block
def switch_off_awg(setup: Setup = None):
    """Switches off the wave generators.

    Args:
        setup (Setup): Setup from which to extract the information from the wave generators.
    """

    setup = setup or load_setup()

    awg1: Tgf4000Interface = setup.gse.wave_generators.awg1.device
    awg2: Tgf4000Interface = setup.gse.wave_generators.awg2.device

    for awg, channel in zip((awg1, awg1, awg2), (1, 2, 1)):
        awg.set_channel(channel)
        awg.set_sweep(Sweep.OFF)
        awg.set_output(Output.OFF)


@building_block
def characterize_piezo(
    piezo: str,
    amplitude: float,
    dc_offset: float,
    start_frequency: float,
    stop_frequency: float,
    sweep_time: float,
    fixed_voltage: float,
    setup: Setup = None,
) -> None:
    """Charactersisation of the given piezo actuator.

    For the given piezo actuator, we configure (and switch on) a frequency sweep.  For the other piezo actuators, we
    configure a constant voltage.

    Args:
        piezo (str): Name of the piezo actuator for which to configure a frequency sweep.
        amplitude (str): Amplitude for the frequency sweep [Vpp].
        dc_offset (str): DC offset for the frequency sweep [Vdc].
        start_frequency (float): Start frequency for the frequency sweep [Hz].
        stop_frequency (float): Stop frequency for the frequency sweep [Hz].
        sweep_time (float): Frequency sweep time [s].
        fixed_voltage (float): Fixed voltage for the other piezo actuators.
        setup (Setup): Setup from which to extract the information from the piezo actuators and corresponding Wave
                       Generators.
    """

    setup = setup or load_setup()

    wave_generators_setup = setup.gse.wave_generators

    awg_list = []
    channel_list = []

    # Loop over all wave generators
    for _, awg in wave_generators_setup.items():
        if "piezo_channels" in awg:  # Exclude the calibration block
            for piezo_name, channel in awg.piezo_channels.items():
                # We configure all channels before turning on their output.  We will first turn on the output for the
                # channels with a constant voltage and then the output for the channels with the frequency sweep (this
                # is why the order in which information is added to `awg_list` and `channel_list`) matters (appending
                # for the channels with constant voltage, prepending for the channel with the frequency sweep).

                if piezo_name == piezo:
                    # Make sure the output for this channel is turned on last

                    awg_list.append(awg)
                    channel_list.append(channel)

                    # Configure the frequency sweep

                    awg.set_channel(channel)
                    awg.set_waveform_shape(WaveformShape.SINE)
                    awg.set_amplitude(amplitude)
                    awg.set_dc_offset(dc_offset)
                    awg.set_output_load(50)

                    awg.set_sweep_type(SweepType.LINUP)
                    awg.set_sweep_mode(SweepMode.CONTINUOUS)
                    awg.set_sweep_start_frequency(start_frequency)
                    awg.set_sweep_stop_frequency(stop_frequency)
                    awg.set_sweep_time(sweep_time)

                    awg.set_sweep(Sweep.ON)
                else:
                    # Make sure the output for the channels with constant voltages are turned on first (i.e. before
                    # switching on the output for the channel with the frequency sweep)

                    awg_list.insert(0, awg)
                    channel_list.insert(0, channel)

                    # Configure the constant voltage

                    awg.set_channel(channel)
                    awg.set_waveform_shape(WaveformShape.ARB)
                    awg.set_arb_waveform(OutputWaveformType.DC)
                    awg.set_dc_offset(fixed_voltage)

    # Turn on the output for all channels (the ones with constant voltage are done before the channel with the
    # frequency sweep -> this is enforced by the way `awg_list` and `channel_list` are populated)

    for awg, channel in zip(awg_list, channel_list):
        awg.set_channel(channel)
        awg.set_output(Output.ON)
