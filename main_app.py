from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from modules import config
from modules.dataman_tcp_client import DataManError, DataManImage, DataManTCPClient


class CutEdgeLabelApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        config.ensure_directories()

        self.title(config.APP_NAME)
        self.geometry("1280x780")
        self.minsize(1100, 680)

        self.current_image: Image.Image | None = None
        self.current_source: str = ""
        self.current_dataman_image: DataManImage | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None

        self.material_var = tk.StringVar(value=config.MATERIAL_LABELS[0])
        self.espesor_var = tk.IntVar(value=config.ESPESORES_MM[0])
        self.etiqueta_var = tk.StringVar(value="sin_clasificar")
        self.operador_var = tk.StringVar(value=config.DEFAULT_OPERATOR)
        self.status_var = tk.StringVar(value="Listo. Capture desde DataMan o cargue una imagen local para prueba.")

        self.rebaba_presente = tk.BooleanVar(value=False)
        self.rebaba_grado = tk.DoubleVar(value=0.0)

        self.estrias_presente = tk.BooleanVar(value=False)
        self.estrias_grado = tk.DoubleVar(value=0.0)
        self.estrias_localizacion = tk.StringVar(value="no_aplica")

        self.oxidacion_presente = tk.BooleanVar(value=False)
        self.oxidacion_grado = tk.DoubleVar(value=0.0)

        self.falta_corte_presente = tk.BooleanVar(value=False)
        self.falta_corte_grado = tk.DoubleVar(value=0.0)
        self.falta_corte_tipo = tk.StringVar(value="no_aplica")

        self.sobrecalentamiento_presente = tk.BooleanVar(value=False)
        self.sobrecalentamiento_grado = tk.DoubleVar(value=0.0)

        self.deformacion_presente = tk.BooleanVar(value=False)
        self.deformacion_grado = tk.DoubleVar(value=0.0)

        self._build_ui()
        self.etiqueta_var.trace_add("write", lambda *_: self._on_etiqueta_changed())

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------
    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        image_frame = ttk.LabelFrame(root, text="Imagen capturada", padding=10)
        image_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)

        self.image_label = ttk.Label(image_frame, text="Sin imagen", anchor="center")
        self.image_label.grid(row=0, column=0, sticky="nsew")

        image_frame.rowconfigure(1, weight=0)
        self._build_terminal_controls(image_frame)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=1, sticky="nsew")
        controls.columnconfigure(0, weight=1)

        self._build_capture_controls(controls)
        self._build_process_controls(controls)
        self._build_defect_controls(controls)
        self._build_notes_controls(controls)
        self._build_save_controls(controls)

        status = ttk.Label(root, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _build_terminal_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Terminal DataMan", padding=4)
        frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        frame.columnconfigure(0, weight=1)

        self.terminal_text = tk.Text(
            frame,
            height=5,
            wrap="word",
            state="disabled",
        )
        self.terminal_text.grid(row=0, column=0, sticky="ew")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.terminal_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.terminal_text.configure(yscrollcommand=scrollbar.set)

    def _append_terminal(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal_text.configure(state="normal")
        self.terminal_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.terminal_text.see(tk.END)
        self.terminal_text.configure(state="disabled")

    def _clear_terminal(self) -> None:
        self.terminal_text.configure(state="normal")
        self.terminal_text.delete("1.0", tk.END)
        self.terminal_text.configure(state="disabled")

    def _build_capture_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Captura", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        self.capture_btn = ttk.Button(
            frame,
            text="Capturar DataMan",
            command=self.capture_dataman,
        )
        self.capture_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.load_btn = ttk.Button(
            frame,
            text="Cargar imagen local",
            command=self.load_local_image,
        )
        self.load_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        info = f"DataMan {config.DATAMAN_IP}:{config.DATAMAN_PORT} | La app no configura la camara"
        ttk.Label(frame, text=info).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_process_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Proceso", padding=8)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Material").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        material = ttk.Combobox(
            frame,
            textvariable=self.material_var,
            values=config.MATERIAL_LABELS,
            state="readonly",
        )
        material.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Espesor material (mm)").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        espesor = ttk.Combobox(
            frame,
            textvariable=self.espesor_var,
            values=config.ESPESORES_MM,
            state="readonly",
        )
        espesor.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Etiqueta principal").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        etiqueta = ttk.Combobox(
            frame,
            textvariable=self.etiqueta_var,
            values=config.ETIQUETAS_PRINCIPALES,
            state="readonly",
        )
        etiqueta.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Operador").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=2)
        operador = ttk.Entry(frame, textvariable=self.operador_var)
        operador.grid(row=3, column=1, sticky="ew", pady=2)

    def _build_defect_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Variables de defecto", padding=8)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(1, weight=1)

        grade_header = ttk.Frame(frame)
        grade_header.grid(row=0, column=1, sticky="ew", pady=(0, 2))
        grade_header.columnconfigure(0, weight=1)
        grade_header.columnconfigure(1, weight=1)
        ttk.Label(grade_header, text="muy poco").grid(row=0, column=0, sticky="w")
        ttk.Label(grade_header, text="mucho").grid(row=0, column=1, sticky="e", padx=(0, 42))

        self._add_defect_slider(frame, 1, "rebaba", self.rebaba_presente, self.rebaba_grado)

        self._add_defect_slider(frame, 2, "estrias", self.estrias_presente, self.estrias_grado)
        ttk.Label(frame, text="estrias_localizacion").grid(row=3, column=0, sticky="w", padx=(20, 8), pady=2)
        loc = ttk.Combobox(
            frame,
            textvariable=self.estrias_localizacion,
            values=config.ESTRIAS_LOCALIZACION,
            state="readonly",
            width=16,
        )
        loc.grid(row=3, column=1, sticky="w", pady=2)

        self._add_defect_slider(frame, 4, "oxidacion_coloracion", self.oxidacion_presente, self.oxidacion_grado)

        self._add_defect_slider(frame, 5, "falta_corte", self.falta_corte_presente, self.falta_corte_grado)
        ttk.Label(frame, text="falta_corte_tipo").grid(row=6, column=0, sticky="w", padx=(20, 8), pady=2)
        fct = ttk.Combobox(
            frame,
            textvariable=self.falta_corte_tipo,
            values=config.FALTA_CORTE_TIPO,
            state="readonly",
            width=16,
        )
        fct.grid(row=6, column=1, sticky="w", pady=2)

        self._add_defect_slider(frame, 7, "sobrecalentamiento", self.sobrecalentamiento_presente, self.sobrecalentamiento_grado)
        self._add_defect_slider(frame, 8, "deformacion_pieza", self.deformacion_presente, self.deformacion_grado)

    def _add_defect_slider(
        self,
        parent: ttk.Frame,
        row: int,
        name: str,
        present_var: tk.BooleanVar,
        grade_var: tk.DoubleVar,
    ) -> None:
        ttk.Checkbutton(parent, text=name, variable=present_var).grid(
            row=row, column=0, sticky="w", pady=2
        )

        sub = ttk.Frame(parent)
        sub.grid(row=row, column=1, sticky="ew", pady=2)
        sub.columnconfigure(0, weight=1)

        value_var = tk.StringVar(value="0.00")

        def on_change(value: str) -> None:
            value_var.set(f"{float(value):.2f}")

        slider = ttk.Scale(
            sub,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=grade_var,
            command=on_change,
        )
        slider.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(sub, textvariable=value_var, width=5).grid(row=0, column=1, sticky="e")

    def _build_notes_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Observaciones", padding=8)
        frame.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)

        self.notes_text = tk.Text(frame, height=4, wrap="word")
        self.notes_text.grid(row=0, column=0, sticky="ew")

    def _build_save_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=4, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Button(frame, text="Guardar etiqueta", command=self.save_label).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ttk.Button(frame, text="Descartar", command=self.discard_current).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(frame, text="Limpiar", command=self.clear_form).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )

    # --------------------------------------------------------
    # Capture and image handling
    # --------------------------------------------------------
    def capture_dataman(self) -> None:
        self.capture_btn.configure(state="disabled")
        self.load_btn.configure(state="disabled")
        self._clear_terminal()
        self._append_terminal("Modo DataMan iniciado.")
        self._append_terminal(
            f"Destino {config.DATAMAN_IP}:{config.DATAMAN_PORT} | "
            f"connect_timeout={config.DATAMAN_CONNECT_TIMEOUT_S}s | "
            f"read_timeout={config.DATAMAN_READ_TIMEOUT_S}s | "
            f"reintentos={config.DATAMAN_CAPTURE_RETRIES}"
        )
        self.status_var.set("Conectando a DataMan. Los mensajes aparecen en Terminal DataMan.")

        import threading

        def log_to_ui(message: str) -> None:
            self.after(0, lambda msg=message: self._append_terminal(msg))

        def worker() -> None:
            try:
                image = DataManTCPClient().capture_once(log_callback=log_to_ui)
            except Exception as exc:  # noqa: BLE001 - show controlled UI error
                self.after(0, lambda err=exc: self._capture_failed(err))
                return
            self.after(0, lambda img=image: self._capture_succeeded(img))

        threading.Thread(target=worker, daemon=True).start()

    def _capture_succeeded(self, image: DataManImage) -> None:
        self.capture_btn.configure(state="normal")
        self.load_btn.configure(state="normal")
        self.current_dataman_image = image
        self.current_source = "DataMan TCP"

        try:
            pil_image = Image.open(BytesIO(image.image_bytes)).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            self.current_image = None
            self.status_var.set("Imagen recibida, pero no se pudo abrir.")
            messagebox.showerror("Imagen no valida", str(exc))
            return

        self.current_image = pil_image
        self._show_image(pil_image)
        summary = (
            f"Imagen recibida: {image.filename or 'sin_nombre'} | "
            f"{image.image_size} bytes | {image.image_format} | endian={image.endian}"
        )
        self._append_terminal(summary)
        self.status_var.set(summary)

    def _capture_failed(self, exc: Exception) -> None:
        self.capture_btn.configure(state="normal")
        self.load_btn.configure(state="normal")
        if isinstance(exc, DataManError):
            message = str(exc)
        else:
            message = f"Error inesperado: {exc}"
        self._append_terminal(f"Captura fallida: {message}")
        self.status_var.set("Fallo de captura DataMan. Revise Terminal DataMan.")

    def load_local_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imagenes", "*.png *.jpg *.jpeg *.bmp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return

        try:
            image = Image.open(path).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Imagen no valida", str(exc))
            return

        self.current_image = image
        self.current_source = "local_file"
        self.current_dataman_image = None
        self._show_image(image)
        self.status_var.set(f"Imagen local cargada: {Path(path).name}")
        self._append_terminal(f"Imagen local cargada para prueba: {Path(path).name}")

    def _show_image(self, image: Image.Image) -> None:
        preview = image.copy()
        preview.thumbnail((760, 520))
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.image_label.configure(image=self.preview_photo, text="")

    # --------------------------------------------------------
    # Form logic
    # --------------------------------------------------------
    def _on_etiqueta_changed(self) -> None:
        etiqueta = self.etiqueta_var.get()
        if etiqueta == "bueno":
            self._clear_defects()
            return

        if etiqueta in config.DEFECTOS:
            self._clear_defects()
            self._set_defect_present(etiqueta, True)

    def _set_defect_present(self, name: str, present: bool) -> None:
        mapping = {
            "rebaba": self.rebaba_presente,
            "estrias": self.estrias_presente,
            "oxidacion_coloracion": self.oxidacion_presente,
            "falta_corte": self.falta_corte_presente,
            "sobrecalentamiento": self.sobrecalentamiento_presente,
            "deformacion_pieza": self.deformacion_presente,
        }
        mapping[name].set(present)

    def _clear_defects(self) -> None:
        self.rebaba_presente.set(False)
        self.rebaba_grado.set(0.0)

        self.estrias_presente.set(False)
        self.estrias_grado.set(0.0)
        self.estrias_localizacion.set("no_aplica")

        self.oxidacion_presente.set(False)
        self.oxidacion_grado.set(0.0)

        self.falta_corte_presente.set(False)
        self.falta_corte_grado.set(0.0)
        self.falta_corte_tipo.set("no_aplica")

        self.sobrecalentamiento_presente.set(False)
        self.sobrecalentamiento_grado.set(0.0)

        self.deformacion_presente.set(False)
        self.deformacion_grado.set(0.0)

    def clear_form(self) -> None:
        self.current_image = None
        self.current_dataman_image = None
        self.current_source = ""
        self.preview_photo = None
        self.image_label.configure(image="", text="Sin imagen")
        self.material_var.set(config.MATERIAL_LABELS[0])
        self.espesor_var.set(config.ESPESORES_MM[0])
        self.etiqueta_var.set("sin_clasificar")
        self._clear_defects()
        self.notes_text.delete("1.0", tk.END)
        self.status_var.set("Formulario limpio.")

    def discard_current(self) -> None:
        self.etiqueta_var.set("descartada")
        self.save_label()

    # --------------------------------------------------------
    # Save dataset
    # --------------------------------------------------------
    def save_label(self) -> None:
        if self.current_image is None:
            messagebox.showwarning("Sin imagen", "No hay imagen activa para guardar.")
            return

        try:
            payload, image_path, label_path = self._build_and_save_payload()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error guardando etiqueta", str(exc))
            return

        self._append_manifests(payload)
        self.status_var.set(f"Guardado: {image_path.name} | {label_path.name}")
        messagebox.showinfo("Guardado", f"Imagen y JSON guardados:\n{image_path}\n{label_path}")

    def _build_and_save_payload(self) -> tuple[dict[str, Any], Path, Path]:
        capture_id = self._build_capture_id()
        image_file_name = f"{capture_id}.png"
        image_path = config.IMAGES_DIR / image_file_name
        label_path = config.LABELS_DIR / f"{capture_id}.json"

        self._save_current_image_as_png(image_path)

        payload = self._build_payload(capture_id, image_file_name)
        label_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload, image_path, label_path

    def _save_current_image_as_png(self, image_path: Path) -> None:
        if self.current_image is None:
            raise RuntimeError("No current image.")
        config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.current_image.save(image_path, format="PNG")

    def _build_capture_id(self) -> str:
        now = datetime.now()
        sequence = self._next_sequence()
        return f"cutedge_{now.strftime('%Y%m%d_%H%M%S')}_{sequence:06d}"

    def _next_sequence(self) -> int:
        existing = list(config.LABELS_DIR.glob("cutedge_*.json"))
        return len(existing) + 1

    def _build_payload(self, capture_id: str, image_file_name: str) -> dict[str, Any]:
        material_label = self.material_var.get()
        if material_label not in config.MATERIALS:
            raise ValueError(f"Material no permitido: {material_label}")

        material_cfg = config.MATERIALS[material_label]
        etiqueta = self.etiqueta_var.get()
        estado = self._estado_from_etiqueta(etiqueta)
        notes = self.notes_text.get("1.0", tk.END).strip()

        dataman_original = None
        if self.current_dataman_image is not None:
            dataman_original = {
                "filename": self.current_dataman_image.filename,
                "image_size": self.current_dataman_image.image_size,
                "image_type": self.current_dataman_image.image_type,
                "image_format": self.current_dataman_image.image_format,
                "endian": self.current_dataman_image.endian,
            }

        return {
            "schema_version": config.SCHEMA_VERSION,
            "capture_id": capture_id,
            "created_at": datetime.now().replace(microsecond=0).isoformat(),
            "image": {
                "file_name": image_file_name,
                "relative_path": f"images/{image_file_name}",
                "format": "PNG",
            },
            "source": {
                "device": config.DATAMAN_DEVICE,
                "connection_mode": config.DATAMAN_CONNECTION_MODE,
                "dataman_ip": config.DATAMAN_IP,
                "dataman_port": config.DATAMAN_PORT,
                "capture_source": self.current_source,
                "dataman_original": dataman_original,
            },
            "camera_settings_observed": config.CAMERA_SETTINGS_OBSERVED,
            "process": {
                "material_tipo": material_cfg["material_tipo"],
                "material_label": material_label,
                "gas_tipo": material_cfg["gas_tipo"],
                "espesor_material": int(self.espesor_var.get()),
            },
            "label": {
                "etiqueta_principal": etiqueta,
                "estado": estado,
            },
            "defectos": self._build_defectos_payload(),
            "operator": {
                "name": self.operador_var.get().strip(),
            },
            "notes": notes,
        }

    def _build_defectos_payload(self) -> dict[str, Any]:
        material_label = self.material_var.get()

        return {
            "rebaba": {
                "presente": bool(self.rebaba_presente.get()),
                "grado_float": self._grade(self.rebaba_grado),
                "grado_categoria": self._rebaba_categoria(self._grade(self.rebaba_grado), material_label, self.rebaba_presente.get()),
            },
            "estrias": {
                "presente": bool(self.estrias_presente.get()),
                "estrias_localizacion": self.estrias_localizacion.get() if self.estrias_presente.get() else "no_aplica",
                "estrias_grado": self._bma_categoria(self._grade(self.estrias_grado), self.estrias_presente.get()),
                "grado_float": self._grade(self.estrias_grado),
            },
            "oxidacion_coloracion": {
                "presente": bool(self.oxidacion_presente.get()),
                "grado_float": self._grade(self.oxidacion_grado),
                "grado_categoria": self._bma_categoria(self._grade(self.oxidacion_grado), self.oxidacion_presente.get()),
            },
            "falta_corte": {
                "presente": bool(self.falta_corte_presente.get()),
                "falta_corte_tipo": self.falta_corte_tipo.get() if self.falta_corte_presente.get() else "no_aplica",
                "grado_float": self._grade(self.falta_corte_grado),
            },
            "sobrecalentamiento": {
                "presente": bool(self.sobrecalentamiento_presente.get()),
                "grado_float": self._grade(self.sobrecalentamiento_grado),
                "grado_categoria": self._bma_categoria(
                    self._grade(self.sobrecalentamiento_grado),
                    self.sobrecalentamiento_presente.get(),
                ),
            },
            "deformacion_pieza": {
                "presente": bool(self.deformacion_presente.get()),
                "grado_float": self._grade(self.deformacion_grado),
                "grado_categoria": self._bma_categoria(self._grade(self.deformacion_grado), self.deformacion_presente.get()),
            },
        }

    @staticmethod
    def _grade(var: tk.DoubleVar) -> float:
        value = float(var.get())
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return round(value, 3)

    @staticmethod
    def _bma_categoria(value: float, present: bool) -> str:
        if not present:
            return "no_aplica"
        if value <= 0.33:
            return "baja"
        if value <= 0.66:
            return "media"
        return "alta"

    @staticmethod
    def _rebaba_categoria(value: float, material_label: str, present: bool) -> str:
        if not present:
            return "no_aplica"
        if material_label == "Acero al carbono O2":
            return "corta_blanda" if value <= 0.5 else "larga_dura"
        if value <= 0.33:
            return "corta"
        if value <= 0.66:
            return "media"
        return "larga"

    @staticmethod
    def _estado_from_etiqueta(etiqueta: str) -> str:
        if etiqueta == "descartada":
            return "descartada"
        if etiqueta == "sin_clasificar":
            return "sin_clasificar"
        return "etiquetada"

    def _append_manifests(self, payload: dict[str, Any]) -> None:
        config.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

        row = self._manifest_row(payload)
        file_exists = config.MANIFEST_CSV.exists()
        with config.MANIFEST_CSV.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        with config.MANIFEST_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _manifest_row(payload: dict[str, Any]) -> dict[str, Any]:
        defectos = payload["defectos"]
        return {
            "schema_version": payload["schema_version"],
            "capture_id": payload["capture_id"],
            "created_at": payload["created_at"],
            "image_relative_path": payload["image"]["relative_path"],
            "material_tipo": payload["process"]["material_tipo"],
            "material_label": payload["process"]["material_label"],
            "gas_tipo": payload["process"]["gas_tipo"],
            "espesor_material": payload["process"]["espesor_material"],
            "etiqueta_principal": payload["label"]["etiqueta_principal"],
            "estado": payload["label"]["estado"],
            "rebaba_presente": defectos["rebaba"]["presente"],
            "rebaba_grado_float": defectos["rebaba"]["grado_float"],
            "rebaba_grado_categoria": defectos["rebaba"]["grado_categoria"],
            "estrias_presente": defectos["estrias"]["presente"],
            "estrias_localizacion": defectos["estrias"]["estrias_localizacion"],
            "estrias_grado": defectos["estrias"]["estrias_grado"],
            "estrias_grado_float": defectos["estrias"]["grado_float"],
            "oxidacion_coloracion_presente": defectos["oxidacion_coloracion"]["presente"],
            "oxidacion_coloracion_grado_float": defectos["oxidacion_coloracion"]["grado_float"],
            "oxidacion_coloracion_grado_categoria": defectos["oxidacion_coloracion"]["grado_categoria"],
            "falta_corte_presente": defectos["falta_corte"]["presente"],
            "falta_corte_tipo": defectos["falta_corte"]["falta_corte_tipo"],
            "falta_corte_grado_float": defectos["falta_corte"]["grado_float"],
            "sobrecalentamiento_presente": defectos["sobrecalentamiento"]["presente"],
            "sobrecalentamiento_grado_float": defectos["sobrecalentamiento"]["grado_float"],
            "sobrecalentamiento_grado_categoria": defectos["sobrecalentamiento"]["grado_categoria"],
            "deformacion_pieza_presente": defectos["deformacion_pieza"]["presente"],
            "deformacion_pieza_grado_float": defectos["deformacion_pieza"]["grado_float"],
            "deformacion_pieza_grado_categoria": defectos["deformacion_pieza"]["grado_categoria"],
            "operator_name": payload["operator"]["name"],
            "notes": payload["notes"],
        }


def main() -> None:
    app = CutEdgeLabelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
