# EtiquetaSeparador

Aplicación de escritorio para extraer etiquetas de envío desde archivos PDF y guardarlas como imágenes individuales.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Descripción

EtiquetaSeparador automatiza el proceso de extraer etiquetas de envío desde PDFs que contienen múltiples etiquetas por página. La aplicación:

- Detecta automáticamente los números de venta (formato `Venta: SXXXXX`)
- Extrae cada etiqueta como imagen individual
- Organiza las imágenes en carpetas por fecha
- Guarda en formato JPEG de alta calidad (95%)

## Captura de Pantalla

```
┌─────────────────────────────────────────┐
│      📦 Etiqueta Separador              │
│                                         │
│   Convierte PDFs de etiquetas en        │
│   imágenes individuales                 │
│                                         │
│   📄 archivo_seleccionado.pdf           │
│                                         │
│   [📁 Seleccionar PDF]                  │
│                                         │
│   [⚡ Procesar Etiquetas]               │
│                                         │
│   ████████████████░░░░ 75%              │
│                                         │
│   > Página 3/4 procesada - 6 etiquetas  │
└─────────────────────────────────────────┘
```

## Requisitos del PDF

La aplicación espera PDFs con el siguiente formato:

- **Layout:** 1 columna × 6 filas de etiquetas por página
- **Identificador:** Cada etiqueta debe contener `Venta: SXXXXX` (donde X son dígitos)
- **Fecha:** El PDF debe contener una fecha en formato `DD/MM/YYYY` para organizar la salida

### Ejemplo de estructura esperada:

```
┌─────────────────────┐
│  Etiqueta 1         │
│  Venta: S12345      │
├─────────────────────┤
│  Etiqueta 2         │
│  Venta: S12346      │
├─────────────────────┤
│  ...                │
├─────────────────────┤
│  Etiqueta 6         │
│  Venta: S12350      │
└─────────────────────┘
```

## Instalación

### Opción 1: Ejecutable (Recomendado para usuarios finales)

Descarga el ejecutable desde [Releases](../../releases):

- **Windows:** `EtiquetaSeparador.exe`
- **macOS:** `EtiquetaSeparador`

No requiere instalación. Solo ejecutar.

### Opción 2: Desde código fuente

```bash
# Clonar repositorio
git clone https://github.com/jnrivra/etiquetatron.git
cd etiquetatron

# Crear entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

## Uso

1. **Abrir** la aplicación
2. **Seleccionar** un archivo PDF con etiquetas
3. **Procesar** haciendo clic en el botón verde
4. **Resultado:** Las imágenes se guardan en `etiquetas/YYYY-MM-DD/`

La carpeta de salida se abre automáticamente al terminar.

## Estructura de Salida

```
etiquetas/
└── 2024-01-15/
    ├── S12345.jpg
    ├── S12346.jpg
    ├── S12347.jpg
    └── ...
```

Si hay números de venta duplicados, se nombran incrementalmente:
- `S12345.jpg`
- `S12345_2.jpg`
- `S12345_3.jpg`

## Compilar Ejecutables

### Windows

```batch
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "EtiquetaSeparador" main.py
```

El ejecutable se genera en `dist/EtiquetaSeparador.exe`

### macOS

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "EtiquetaSeparador" main.py
```

El ejecutable se genera en `dist/EtiquetaSeparador`

## Dependencias

| Paquete | Versión | Descripción |
|---------|---------|-------------|
| customtkinter | 5.2.1 | Interfaz gráfica moderna |
| PyMuPDF | 1.23.8 | Procesamiento de PDFs |
| Pillow | 10.2.0 | Manipulación de imágenes |
| pyinstaller | 6.3.0 | Generación de ejecutables |

## Personalización

Los parámetros de recorte están calibrados para un layout específico. Si tu PDF tiene un formato diferente, puedes ajustar estos valores en `main.py`:

```python
margin_x = 29          # Margen izquierdo en píxeles
first_y = 12           # Posición Y de la primera etiqueta
spacing = 376          # Espacio entre etiquetas
label_height = 355     # Altura de cada etiqueta
```

## Licencia

MIT License - ver [LICENSE](LICENSE) para más detalles.

## Autor

Desarrollado para automatizar procesos de logística y envíos.
