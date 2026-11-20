# Guía de entrenamiento – EcoSort AI

## Flujo completo
**Descargar dataset → anotar → entrenar → exportar → desplegar**

### 1. Descargar un dataset
- **TACO** (Trash Annotations in Context): http://tacodataset.org — anotaciones COCO, hay que convertirlas a formato YOLO.
- **TrashNet**: https://github.com/garythung/trashnet — solo clasificación (una clase por imagen); necesitas anotar cajas.
- **Waste Detection (Roboflow Universe)**: https://universe.roboflow.com — busca "waste detection", exporta en formato **YOLOv8**.

Revisa la licencia de cada dataset antes de usarlo.

### 2. Anotar (si hace falta)
Herramientas: Roboflow, CVAT, Label Studio o LabelImg. Exporta en formato YOLO (`.txt` por imagen: `clase x_centro y_centro ancho alto`, normalizados). Unifica las clases a: `plastic, metal, glass, paper, organic, cardboard` (y opcionalmente `trash`). Mínimo recomendado: **300+ imágenes por clase**, con fondos, luces y ángulos variados.

### 3. Estructura y data.yaml
```
dataset/
├── images/{train,val,test}/
└── labels/{train,val,test}/
```
```yaml
# data.yaml
path: /ruta/absoluta/a/dataset
train: images/train
val: images/val
test: images/test
names:
  0: plastic
  1: metal
  2: glass
  3: paper
  4: organic
  5: cardboard
```
Los nombres deben coincidir con `CLASSES`/`POINTS_SYSTEM` en `config.py`.

### 4. Entrenar
```bash
python train.py --data data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --batch 16 --device 0
```
Genera `runs/ecosort/weights/best.pt`, copia el modelo a `models/best.pt`, exporta `best_ncnn_model/` y escribe `training_log.txt` (mAP50, mAP50-95, precision, recall).

### 5. Exportar y desplegar
- **PC/Streamlit**: usa `models/best.pt` (automático).
- **Raspberry Pi**: copia la carpeta `best_ncnn_model/` a `models/` en la Pi y arranca `ecosort.service`.

## Hiperparámetros recomendados
| Escenario | Modelo | epochs | imgsz | batch |
|-----------|--------|--------|-------|-------|
| Raspberry Pi (rápido) | yolov8n | 100–150 | 320–416 | 16–32 |
| PC con GPU | yolov8s | 100–200 | 640 | 16 |
| Máxima precisión | yolov8m | 150–300 | 640 | 8–16 |

- Sin GPU: `--device cpu`, `yolov8n`, `--batch 8` y menos épocas.
- Si hay sobreajuste (val loss sube): más datos/augmentation o menos épocas.
- Clases desbalanceadas: añade imágenes de las clases débiles.
- Revisa la matriz de confusión en `runs/ecosort/`; vidrio/plástico transparente suele confundirse.

## Idioma de las etiquetas (español)
- La interfaz muestra los nombres en español (`CLASS_NAMES_ES` en `config.py`), aunque el dataset esté en inglés.
- Si tu dataset está etiquetado en español (`plastico, metal, vidrio, papel, organico, carton, basura`), funciona sin cambios: `SPANISH_ALIASES` los convierte a las claves internas.
- Para añadir otra etiqueta o sinónimo, agrégala a `SPANISH_ALIASES` (español) o `CLASS_ALIASES` (otros nombres).
