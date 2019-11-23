from cocotb.bus import ClockedBus


class AvalonMMBus(ClockedBus):
    """Avalon Memory Mapped Interface (Avalon-MM) Bus."""

    _signals = ["address"]
    _optional_signals = [
        "read", "readdata", "readdatavalid", "write", "writedata",
        "waitrequest", "burstcount", "byteenable", "cs",
    ]


class AvalonSTBus(ClockedBus):
    """Avalon Streaming Interface (Avalon-ST) Bus."""

    _signals = ["valid", "data"]
    _optional_signals = ["ready"]


class AvalonSTPktsBus(ClockedBus):
    """Avalon Streaming Interface (Avalon-ST) Packetized Bus."""

    _signals = ["valid", "data", "startofpacket", "endofpacket"]
    _optional_signals = ["error", "channel", "ready", "empty"]
