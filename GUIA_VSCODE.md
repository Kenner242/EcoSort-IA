# Guía rápida para VS Code

## Abrir el proyecto
1. Descomprime `ecosort_ai.zip`.
2. VS Code → **Archivo → Abrir carpeta…** → selecciona `ecosort_ai` (la carpeta que contiene `app.py`).
3. Acepta "Instalar extensiones recomendadas".

## Instalar
- **Windows:** doble clic en `setup_windows.bat`.
- **Mac/Linux:** `bash setup_mac_linux.sh`.
- Después: `Ctrl+Shift+P` → *Python: Select Interpreter* → `venv`.

> En Mac/Linux cambia en `.vscode/settings.json` la ruta del intérprete a `${workspaceFolder}/venv/bin/python` (o simplemente selecciónalo con el comando anterior).

## Ejecutar (panel "Ejecutar y depurar", `Ctrl+Shift+D`)
| Opción | Qué hace |
|--------|----------|
| 1) Dashboard Streamlit | Abre la app web |
| 2) Probar detector | Prueba con imagen en blanco |
| 3) Probar gamificación | Simula 3 escaneos y muestra el leaderboard |
| 4) Preparar dataset | Split train/val/test |
| 5) Entrenar (prueba rápida) | 5 épocas en CPU |
| 6) Evaluar en test | Métricas por clase en `reports/` |
| 7) Controlador Raspberry (mock) | Simula los servos en PC |

Pruebas: ícono del matraz (Testing) o `python -m pytest -v test_detector.py`.
Tareas: `Ctrl+Shift+P` → *Tasks: Run Task*.

## Estructura
```
ecosort_ai/
├── .vscode/            configuración de VS Code (intérprete, depuración, tareas)
├── dataset/raw/        pon aquí images/ y labels/ (formato YOLO)
├── models/             best.pt y best_ncnn_model/
├── reports/            resultados de evaluación
├── scripts/            prepare_dataset.py, evaluate.py
├── app.py  config.py  detector.py  gamification.py  train.py  raspi_controller.py
├── test_detector.py  pytest.ini  data.yaml  requirements.txt
├── setup_windows.bat  setup_mac_linux.sh  install_raspi.sh
└── README.md  TRAINING.md  PLAN_CIENTIFICO.md  GUIA_VSCODE.md
```

## Si algo falla
- *"No module named ..."* → el intérprete no es el `venv`; vuelve a seleccionarlo.
- *Cámara no funciona en Streamlit* → permite la cámara en el navegador (en servidor remoto necesita HTTPS).
- *Primera ejecución lenta* → descarga `yolov8n.pt` (necesita internet).
