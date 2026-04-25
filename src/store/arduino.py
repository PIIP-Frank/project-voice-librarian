import struct
import time

try:
    import serial
    import serial.tools.list_ports as _list_ports
except ImportError:
    serial = None
    _list_ports = None

START_MAGIC = b"\xAA\x55"
END_MAGIC = b"\x55\xAA"


class ArduinoNotAvailable(RuntimeError):
    pass


def is_available() -> bool:
    return serial is not None


def list_ports() -> list[str]:
    if _list_ports is None:
        return []
    return [p.device for p in _list_ports.comports()]


class ArduinoSerial:
    """Minimal client for the Voice Librarian firmware."""

    def __init__(self, port: str, baud: int = 115200):
        if serial is None:
            raise ArduinoNotAvailable(
                "pyserial is not installed — run: pip install pyserial"
            )
        self.port = port
        self.baud = baud
        self._ser = None

    def __enter__(self) -> "ArduinoSerial":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self, settle: float = 1.5, timeout: float = 1.0) -> None:
        self._ser = serial.Serial(self.port, self.baud, timeout=timeout)
        # Native USB CDC boards don't reset on open, but harmless.
        time.sleep(settle)
        self._ser.reset_input_buffer()

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def record(self, seconds: int) -> tuple[bytes, int]:
        """Capture `seconds` of mono int16 PCM.

        Returns (pcm_bytes, sample_rate). The rate is derived from the actual
        payload length the firmware sent — the firmware is the source of truth
        because the PDM peripheral only supports certain rates.
        """
        if self._ser is None:
            raise ArduinoNotAvailable("Serial port not open")

        s = self._ser
        s.reset_input_buffer()
        s.write(f"R{seconds}\n".encode("ascii"))
        s.flush()

        deadline = time.monotonic() + seconds + 5.0
        self._wait_for_magic(START_MAGIC, deadline)

        (length,) = struct.unpack("<I", self._read_exact(4, deadline))
        if length == 0 or length % 2 != 0 or length % seconds != 0:
            raise RuntimeError(f"Implausible payload length: {length} bytes")

        payload = self._read_exact(length, deadline)

        end = self._read_exact(2, deadline)
        if end != END_MAGIC:
            raise RuntimeError(f"Bad end marker: {end!r}")

        sample_rate = (length // 2) // seconds
        return payload, sample_rate

    # ── Internals ────────────────────────────────────────────────────────────

    def _read_exact(self, n: int, deadline: float) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timeout reading {n} bytes (got {len(buf)})")
            chunk = self._ser.read(n - len(buf))
            if chunk:
                buf.extend(chunk)
        return bytes(buf)

    def _wait_for_magic(self, magic: bytes, deadline: float) -> None:
        seen = bytearray()
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("Timeout waiting for start marker")
            b = self._ser.read(1)
            if not b:
                continue
            seen.extend(b)
            if seen.endswith(magic):
                return
            if len(seen) > 2048:
                seen = seen[-len(magic):]
