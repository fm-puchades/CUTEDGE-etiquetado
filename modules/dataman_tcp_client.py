from __future__ import annotations

from dataclasses import dataclass
import socket

from modules import config


class DataManError(RuntimeError):
    """Raised when DataMan TCP capture fails."""


@dataclass(frozen=True)
class DataManImage:
    image_bytes: bytes
    image_size: int
    image_type: int
    image_format: str
    filename: str
    endian: str


class DataManTCPClient:
    def __init__(
        self,
        host: str = config.DATAMAN_IP,
        port: int = config.DATAMAN_PORT,
        connect_timeout_s: float = config.DATAMAN_CONNECT_TIMEOUT_S,
        read_timeout_s: float = config.DATAMAN_READ_TIMEOUT_S,
    ) -> None:
        self.host = host
        self.port = port
        self.connect_timeout_s = connect_timeout_s
        self.read_timeout_s = read_timeout_s

    def capture_once(self) -> DataManImage:
        """
        Connect to DataMan Local TCP Server and read one image.

        Expected operator flow:
        1. Click capture in the app.
        2. Python connects to DataMan.
        3. Operator presses physical trigger.
        4. DataMan sends header + image bytes.
        """
        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.connect_timeout_s,
            ) as sock:
                sock.settimeout(self.read_timeout_s)
                header = self._recv_exact(sock, config.DATAMAN_HEADER_SIZE)
                image_size, image_type, filename, endian = self._parse_header(header)
                image_bytes = self._recv_exact(sock, image_size)
        except OSError as exc:
            raise DataManError(f"TCP error with DataMan {self.host}:{self.port}: {exc}") from exc

        image_format = config.DATAMAN_IMAGE_TYPES.get(image_type, "UNKNOWN")
        return DataManImage(
            image_bytes=image_bytes,
            image_size=image_size,
            image_type=image_type,
            image_format=image_format,
            filename=filename,
            endian=endian,
        )

    @staticmethod
    def _recv_exact(sock: socket.socket, n_bytes: int) -> bytes:
        chunks: list[bytes] = []
        remaining = n_bytes

        while remaining > 0:
            chunk = sock.recv(min(remaining, 65536))
            if not chunk:
                received = n_bytes - remaining
                raise DataManError(
                    f"Unexpected end of stream. Expected {n_bytes} bytes, received {received}."
                )
            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)

    @staticmethod
    def _parse_header(header: bytes) -> tuple[int, int, str, str]:
        if len(header) != config.DATAMAN_HEADER_SIZE:
            raise DataManError(
                f"Invalid header length: {len(header)} bytes. Expected {config.DATAMAN_HEADER_SIZE}."
            )

        parsed = None
        for endian in ("little", "big"):
            image_size = int.from_bytes(header[0:4], endian)
            image_type = int.from_bytes(header[4:8], endian)

            if 0 < image_size < 100_000_000 and image_type in config.DATAMAN_IMAGE_TYPES:
                parsed = (image_size, image_type, endian)
                break

        if parsed is None:
            little_size = int.from_bytes(header[0:4], "little")
            little_type = int.from_bytes(header[4:8], "little")
            raise DataManError(
                "Could not parse DataMan header. "
                f"little_size={little_size}, little_type={little_type}"
            )

        image_size, image_type, endian = parsed
        raw_name = header[8:136].split(b"\x00", 1)[0]
        filename = raw_name.decode("utf-8", errors="replace").strip()

        return image_size, image_type, filename, endian
