# ♻️ EcoSort AI

Sistema de clasificación de residuos sólidos mediante cámara con **YOLOv8**, un sistema gamificado de **Eco-Puntos** persistido en SQLite, un dashboard en **Streamlit** y control opcional de contenedores con servomotores en **Raspberry Pi**.

## Características
- Detección de residuos (plástico, metal, vidrio, papel, orgánico, cartón, basura).
- Eco-Puntos solo si la confianza ≥ 0.7; insignias por nivel.
- Prevención de duplicados con hash perceptual (`imagehash.phash`).
- Dashboard con cámara, subida de imágenes y leaderboard (Plotly).
- Entrenamiento con exportación automática a NCNN para Raspberry Pi.

## Instalación en PC
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
> Sin `models/best.pt`, el sistema usa `yolov8n.pt` (COCO) como **modelo demo**: detecta pocos objetos (botellas, tazas, frutas) mapeados a clases de residuos. Para resultados reales entrena tu modelo (ver `TRAINING.md`).

## Instalación en Raspberry Pi
```bash
bash install_raspi.sh
# copia el modelo exportado a models/best_ncnn_model/
sudo systemctl start ecosort
```

## Ejecución
```bash
streamlit run app.py                  # dashboard
python raspi_controller.py            # controlador (en PC usa GPIO simulado)
```

## Entrenamiento
```bash
python train.py --data data.yaml --epochs 100 --device 0
```

## Pruebas
```bash
pytest -v test_detector.py
```

## Estructura
```
ecosort_ai/
├── requirements.txt     dependencias
├── config.py            rutas, puntos, umbrales, clases, insignias
├── detector.py          WasteDetector (YOLOv8)
├── gamification.py      EcoPointsManager (SQLite)
├── app.py               dashboard Streamlit
├── train.py             entrenamiento + exportación NCNN
├── raspi_controller.py  servos GPIO 17/18/27 + bucle de cámara
├── test_detector.py     pruebas pytest
├── install_raspi.sh     instalador para Raspberry Pi + systemd
├── TRAINING.md          guía de entrenamiento
└── README.md
```

## Contenedores (servos)
| GPIO | Contenedor | Clases |
|------|------------|--------|
| 17 | Reciclables | plastic, metal, glass |
| 18 | Papel/cartón | paper, cardboard |
| 27 | Orgánico/otros | organic, trash |

## Guías adicionales
- `GUIA_VSCODE.md`: cómo abrir, instalar y ejecutar en VS Code.
- `PLAN_CIENTIFICO.md`: plan paso a paso (datos, experimentos, evaluación, despliegue).
- `scripts/prepare_dataset.py` y `scripts/evaluate.py`: split reproducible y evaluación por clase.

## Modos de detección (todo en español)
`DETECTION_MODE = "auto"` en `config.py` elige el mejor modelo disponible:
1. **Entrenado** (`models/best.pt`): el más preciso para residuos.
2. **YOLO-World**: reconoce ~43 residuos y objetos sin entrenar. Requiere `pip install -r requirements-openvocab.txt` (necesita Git).
3. **General (COCO)**: 80 objetos comunes; se usa si lo anterior no está disponible.
La app muestra arriba qué modo está activo.

## Impacto ambiental y economía circular
- `impact.py` y la pestaña "Impacto ambiental" de la app estiman kg, tasa de desviación y CO2e (valores orientativos, ver supuestos).
- `ECONOMIA_CIRCULAR.md`: ruta de valorización, indicadores, diseño del piloto y alianzas.
