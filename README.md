# CUTEDGE-etiquetado

Aplicacion de escritorio Tkinter para capturar imagenes desde Cognex DataMan y etiquetarlas manualmente como dataset de entrenamiento.

## Objetivo v0.1

- Conectar a DataMan por TCP.
- Recibir una imagen.
- Mostrar la imagen.
- Elegir material, espesor y etiqueta principal.
- Registrar variables de defecto alineadas con el arbol de diagnostico.
- Guardar todas las imagenes en una unica carpeta.
- Guardar un JSON por imagen.
- Actualizar manifiestos CSV y JSONL.

No se hace diagnostico automatico.
No se hace IA.
No se hacen recomendaciones de parametros.
No se configura la DataMan desde la aplicacion.

## Configuracion actual DataMan

La configuracion de camara se hace manualmente con Cognex Setup Tool.

Ajustes conocidos usados solo como metadatos:

- Exposicion automatica: desactivada
- Tiempo de exposicion: 300 us
- Ganancia: 1.00
- Luz autofocus: activa

Conexion:

```text
IP: 169.254.38.45
Puerto: 2121
Modo: Local TCP Server
```

## Estructura del dataset

```text
dataset_cognex/
  images/
    cutedge_YYYYMMDD_HHMMSS_000001.png
  labels/
    cutedge_YYYYMMDD_HHMMSS_000001.json
  manifests/
    dataset_index.csv
    dataset_index.jsonl
```

No hay carpetas por clase.
La clase y las variables de defecto se guardan en JSON.

## Variables de defecto v0.1

Alineadas con el arbol de diagnostico:

- rebaba
- estrias
- oxidacion_coloracion
- falta_corte
- sobrecalentamiento
- deformacion_pieza

Excluidas:

- kerf: porque la imagen sera del canto/espesor, no del ancho de corte.
- escoria: no se usa en v0.1 para ceñirse al arbol de diagnostico.

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecucion

```bash
python main_app.py
```

## Uso

1. Abrir la aplicacion.
2. Pulsar `Capturar DataMan`.
3. Pulsar el gatillo fisico de la DataMan.
4. Verificar que aparece la imagen.
5. Seleccionar material.
6. Seleccionar espesor.
7. Seleccionar etiqueta principal.
8. Ajustar variables de defecto si procede.
9. Pulsar `Guardar etiqueta`.

Para pruebas sin DataMan se puede usar `Cargar imagen local`.

## Salida JSON

Ejemplo simplificado:

```json
{
  "schema_version": "cutedge_label_v0.1",
  "capture_id": "cutedge_20260604_091522_000001",
  "image": {
    "relative_path": "images/cutedge_20260604_091522_000001.png",
    "format": "PNG"
  },
  "process": {
    "material_tipo": "acero_carbono_n2",
    "gas_tipo": "N2",
    "espesor_material": 8
  },
  "label": {
    "etiqueta_principal": "rebaba",
    "estado": "etiquetada"
  },
  "defectos": {
    "rebaba": {
      "presente": true,
      "grado_float": 0.72,
      "grado_categoria": "larga"
    }
  }
}
```

## Diagnostico red previo

Antes de usar DataMan, verificar desde PowerShell:

```powershell
ping 169.254.38.45
Test-NetConnection 169.254.38.45 -Port 2121
```

El puerto debe devolver:

```text
TcpTestSucceeded : True
```
