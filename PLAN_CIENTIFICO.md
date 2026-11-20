# Plan paso a paso (método científico) – EcoSort AI

Objetivo: construir un clasificador de residuos **medible, reproducible y desplegable**, y validar que el sistema de Eco-Puntos realmente incentiva el reciclaje.

---

## Fase 0 – Preparar el entorno (30 min)
1. Instala **Python 3.10–3.12** (marca "Add to PATH" en Windows) y **VS Code**.
2. Abre la carpeta `ecosort_ai` en VS Code (`Archivo > Abrir carpeta`). Acepta instalar las extensiones recomendadas.
3. Ejecuta `setup_windows.bat` (Windows) o `bash setup_mac_linux.sh` (Mac/Linux). Crea `venv/` e instala todo.
4. `Ctrl+Shift+P` → **Python: Select Interpreter** → elige el del `venv`.
5. Abre la terminal de VS Code y ejecuta `python -m pytest -v test_detector.py`.
   **Criterio de éxito:** 4 tests pasan (si no hay internet, los 2 del detector se omiten).

## Fase 1 – Definir problema e hipótesis (1 h)
- **Problema:** clasificar residuos por cámara en 6–7 categorías.
- **Hipótesis H1:** un YOLOv8n entrenado en tus datos alcanza **mAP50 ≥ 0.75** y **recall ≥ 0.70 por clase**.
- **Hipótesis H2:** el sistema de Eco-Puntos aumenta la cantidad de residuos correctamente separados frente a un grupo sin incentivo.
- Define **métricas antes de entrenar** (así no las ajustas a conveniencia): mAP50, mAP50-95, precision, recall por clase, FPS en la Raspberry Pi.

## Fase 2 – Recolectar datos (1–2 semanas)
1. Descarga datasets públicos (TACO, TrashNet, Roboflow "waste detection"; ver `TRAINING.md`) y **revisa su licencia**.
2. Añade **fotos propias** del lugar real de uso (misma cámara, iluminación y fondo que el contenedor): es lo que más mejora la precisión real.
3. Meta mínima: **300+ imágenes por clase**, con variación de fondo, luz, ángulo y oclusión.
4. Anota en Roboflow/CVAT/LabelImg en formato YOLO y guarda en `dataset/raw/images` y `dataset/raw/labels` (mismo nombre base, `.jpg` y `.txt`).
5. Unifica los nombres de clase con los de `data.yaml` / `config.py`.

## Fase 3 – Dividir los datos sin fuga (30 min)
```bash
python scripts/prepare_dataset.py --source dataset/raw --seed 42
```
- Split **70 % train / 15 % val / 15 % test** con semilla fija (reproducible).
- **Regla de oro:** el conjunto `test` no se toca hasta la Fase 6. Si tomaste varias fotos del mismo objeto, ponlas todas en el mismo split (si no, el test sale inflado).
- Revisa el reporte: ninguna clase debe tener muy pocas imágenes en val/test.

## Fase 4 – Línea base (1 día)
Entrena el modelo más simple y registra el resultado; todo lo demás se compara contra él.
```bash
python train.py --data data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --batch 16 --device 0
```
(Sin GPU: `--device cpu --batch 8 --epochs 50`; en VS Code puedes usar la configuración de depuración **5) Entrenar** para una prueba rápida de 5 épocas primero.)

Guarda `training_log.txt` y la carpeta `runs/ecosort/` (curvas, matriz de confusión). Revisa:
- Curva de pérdida: si la de validación sube mientras la de train baja → sobreajuste.
- Matriz de confusión: ¿qué clases se confunden (p. ej. vidrio vs. plástico transparente)?

## Fase 5 – Experimentos controlados (1–2 semanas)
Cambia **una variable por experimento** y anota los resultados en una tabla (`reports/experimentos.csv` o Excel):

| Exp | Cambio | mAP50 | mAP50-95 | Recall mín. por clase | FPS (Pi) |
|-----|--------|-------|----------|-----------------------|----------|
| E0 | yolov8n, 640 (línea base) | | | | |
| E1 | yolov8s | | | | |
| E2 | imgsz 416 (más rápido en Pi) | | | | |
| E3 | + más datos de clases débiles | | | | |

Repite el mejor experimento con **3 semillas distintas** para saber si la mejora es real o ruido. Prioriza mejorar **datos** antes que cambiar de arquitectura.

## Fase 6 – Evaluación final en test (una sola vez)
```bash
python scripts/evaluate.py --data data.yaml --model models/best.pt
```
Genera `reports/eval_summary.json` y `reports/eval_per_class.csv`. Contrasta con H1 y **reporta también lo que falló**. Si ajustas el modelo después de ver el test, ese test ya no sirve: consigue datos nuevos.

## Fase 7 – Probar el sistema completo (3–5 días)
1. `streamlit run app.py` (o el botón **1) Dashboard Streamlit** en Ejecutar y depurar).
2. Prueba con objetos reales: usuario → foto → detección → confirmar puntos → leaderboard.
3. Verifica los casos límite: imagen sin residuo, confianza < 0.7 (0 puntos), imagen repetida (duplicado rechazado).
4. Umbrales (`config.py`): ajusta `POINTS_THRESHOLD` y `BIN_OPEN_THRESHOLD` según la precisión por clase que midiste, no a ojo.

## Fase 8 – Despliegue en Raspberry Pi (2–3 días)
1. `bash install_raspi.sh` en la Pi; copia `models/best_ncnn_model/`.
2. Conecta los servos (GPIO 17, 18, 27) con **alimentación externa de 5 V** (nunca desde el pin 5 V de la Pi) y **tierra común**.
3. Prueba primero con `python raspi_controller.py` en PC (modo mock) y luego en la Pi.
4. Mide FPS y latencia cámara→servo. Objetivo orientativo: ≥ 5 FPS.

## Fase 9 – Validar el incentivo (H2) (2–4 semanas)
- Diseño: **grupo A** con Eco-Puntos y **grupo B** sin ellos (o antes/después), misma duración.
- Variable medida: % de residuos depositados en el contenedor correcto (conteo manual de una muestra) y número de usos por persona.
- Analiza con una prueba estadística adecuada (p. ej. chi-cuadrado o prueba t) y reporta tamaño del efecto, no solo el p-valor.
- Cuida la privacidad: usa seudónimos, no guardes fotos de personas y pide consentimiento.

## Fase 10 – Documentar y mantener
- Registra versión del modelo, fecha, dataset, semilla y métricas en cada entrenamiento.
- Reentrena cuando bajen las métricas en uso real (nuevos envases, otra iluminación).
- Haz copia de seguridad de `ecosort.db` y `models/best.pt`.

---

### Checklist rápido de calidad
- [ ] Métricas definidas antes de entrenar
- [ ] Split con semilla y sin fuga de datos
- [ ] Línea base registrada
- [ ] Un cambio por experimento, con tabla de resultados
- [ ] Test usado una sola vez
- [ ] Fallos y limitaciones reportados
- [ ] Prueba real de punta a punta antes de instalar en el contenedor
