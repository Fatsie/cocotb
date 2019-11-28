from cocotb.bus import ClockedBus


class WishboneBus(ClockedBus):
    _signals = ["cyc", "stb", "we", "adr", "datwr", "datrd", "ack"]
    _optional_signals = ["sel", "err", "stall", "rty"]
