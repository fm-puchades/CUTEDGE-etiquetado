from __future__ import annotations

from dataclasses import dataclass
import socket
import time
from typing import Callable

from modules import config


LogCallback = Callable[[str], None]


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
        retries: int = config.DATAMAN_CAPTURE_RETRIES,
        retry_delay_s: float = config.DATAMAN_RETRY_DELAY_S,
    ) -> None:
        self.host = host
        self.port = port
        self.connect_timeout_s = connect_timeout_s
        self.read_timeout_s = read_timeout_s
        self.retries = max(1, retries)
        self.retry_delay_s = max(0.0, retry_delay_s)

    def capture_once(self, log_callback: LogCallback | None = None) -> DataManImage:
        """
        Connect to DataMan Local TCP Server and read one image.

        Expected operator flow:
        1. Click capture in the app.
        2. Python connects to DataMan.
        3. Operator presses physical trigger.
        4. DataMan sends header + image bytes.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            self._log(log_callback, f"Intento {attempt}/{self.retries}: conectando a {self.host}:{self.port}")

            try:
                with socket.create_connection(
                    (self.host, self.port),
                    timeout=self.connect_timeout_s,
                ) as sock:
                    self._log(log_callback, "TCP conectado. Pulse el gatillo fisico si aun no lo ha hecho.")
                    sock.settimeout(self.read_timeout_s)

                    self._log(log_callback, f"Esperando cabecera DataMan ({config.DATAMAN_HEADER_SIZE} bytes)...")
                    header = self._recv_exact(
                        sock,
                        config.DATAMAN_HEADER_SIZE,
                        label="cabecera",
                        log_callback=log_callback,
                    )

                    image_size, image_type, filename, endian = self._parse_header(header)
                    image_format = config.DATAMAN_IMAGE_TYPES.get(image_type, "UNKNOWN")
                    self._log(
                        log_callback,
                        "Cabecera recibida: "
                        f"size={image_size}, type={image_type} ({image_format}), "
                        f"filename='{filename}', endian={endian}",
                    )

                    self._log(log_callback, f"Recibiendo imagen ({image_size} bytes)...")
                    image_bytes = self._recv_exact(
                        sock,
                        image_size,
                        label="imagen",
                        log_callback=log_callback,
                    )

                    self._log(log_callback, "Imagen recibida correctamente.")
                    return DataManImage(
                        image_bytes=image_bytes,
                        image_size=image_size,
                        image_type=image_type,
                        image_format=image_format,
                        filename=filename,
                        endian=endian,
                    )

            except (OSError, DataManError) as exc:
                last_error = exc
                self._log(log_callback, f"Fallo en intento {attempt}/{self.retries}: {exc}")

                if attempt < self.retries:
                    self._log(log_callback, f"Reintentando en {self.retry_delay_s:.1f} s...")
                    time.sleep(self.retry_delay_s)

        raise DataManError(
            f"No se pudo capturar desde DataMan {self.host}:{self.port}. Ultimo error: {last_error}"
        )

    @staticmethod
    def _recv_exact(
        sock: socket.socket,
        n_bytes: int,
        label: str,
        log_callback: LogCallback | None = None,
    ) -> bytes:
        chunks: list[bytes] = []
        remaining = n_bytes
        received = 0
        last_reported_mb = -1

        while remaining > 0:
            try:
                chunk = sock.recv(min(remaining, 65536))
            except socket.timeout as exc:
                raise DataManError(
                    f"Timeout esperando {label}. Recibidos {received}/{n_bytes} bytes."
                ) from exc

            if not chunk:
                raise DataManError(
                    f"Cierre inesperado de conexion recibiendo {label}. "
                    f"Recibidos {received}/{n_bytes} bytes."
                )

            chunks.append(chunk)
            received += len(chunk)
            remaining -= len(chunk)

            current_mb = received // 1_000_000
            if n_bytes >= 1_000_000 and current_mb != last_reported_mb:
                last_reported_mb = current_mb
                DataManTCPClient._log(
                    log_callback,
                    f"Recibiendo {label}: {received}/{n_bytes} bytes",
                )

        return b"".join(chunks)

    @staticmethod
    def _parse_header(header: bytes) -> tuple[int, int, str, str]:
        if len(header) != config.DATAMAN_HEADER_SIZE:
            raise DataManError(
                f"Longitud de cabecera no valida: {len(header)} bytes. "
                f"Esperados {config.DATAMAN_HEADER_SIZE}."
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
                "No se pudo interpretar la cabecera DataMan. "
                f"little_size={little_size}, little_type={little_type}"
            )

        image_size, image_type, endian = parsed
        raw_name = header[8:136].split(b"\x00", 1)[0]
        filename = raw_name.decode("utf-8", errors="replace").strip()

        return image_size, image_type, filename, endian

    @staticmethod
    def _log(log_callback: LogCallback | None, message: str) -> None:
        if log_callback is not None:
            log_callback(message)
