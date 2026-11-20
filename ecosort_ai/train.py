"""
train.py - Entrenamiento de YOLOv8 para EcoSort AI.

Valida el dataset, entrena, evalúa, guarda training_log.txt con las métricas
y exporta automáticamente el mejor modelo a NCNN (para Raspberry Pi).

Ejemplo:
    python train.py --data data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --batch 16 --device 0

Ejemplo de data.yaml para 6 clases:
    # data.yaml
    path: /ruta/absoluta/a/dataset      # raíz del dataset
    train: images/train                 # relativo a 'path'
    val: images/val
    test: images/test                   # opcional
    names:
      0: plastic
      1: metal
      2: glass
      3: paper
      4: organic
      5: cardboard
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from config import BASE_DIR, MODELS_DIR, RUNS_DIR

logger = logging.getLogger(__name__)


def validate_dataset(data_yaml_path):
    """Verifica que data.yaml exista y contenga las claves train, val y names.

    Returns:
        dict: contenido del YAML. Lanza FileNotFoundError/ValueError si es inválido.
    """
    path = Path(data_yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo de dataset: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML inválido en {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path} debe contener un diccionario YAML")
    missing = [k for k in ("train", "val", "names") if k not in data]
    if missing:
        raise ValueError(f"Faltan claves en {path}: {', '.join(missing)}")
    if not data["names"]:
        raise ValueError("La clave 'names' está vacía")
    return data


def resolve_device(device):
    """Devuelve un dispositivo válido; si se pide CUDA y no hay, cae a CPU."""
    device = str(device).strip().lower()
    if device in ("", "cpu"):
        return device or "cpu"
    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning("CUDA no disponible; usando CPU.")
            return "cpu"
    except ImportError:
        return "cpu"
    return device


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Entrenamiento YOLOv8 - EcoSort AI")
    parser.add_argument("--data", default="data.yaml", help="ruta a data.yaml")
    parser.add_argument("--model", default="yolov8n.pt", help="modelo base (yolov8n.pt, yolov8s.pt, ...)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cpu", help="'cpu', '0', '0,1' ...")
    return parser.parse_args(argv)


def write_training_log(metrics, args, export_path, log_path):
    """Guarda las métricas finales en training_log.txt."""
    lines = [
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        f"Modelo base: {args.model}",
        f"Dataset: {args.data}",
        f"Epochs: {args.epochs} | imgsz: {args.imgsz} | batch: {args.batch} | device: {args.device}",
        f"mAP50: {metrics.box.map50:.4f}",
        f"mAP50-95: {metrics.box.map:.4f}",
        f"Precision: {metrics.box.mp:.4f}",
        f"Recall: {metrics.box.mr:.4f}",
        f"Exportación NCNN: {export_path}",
    ]
    Path(log_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        validate_dataset(args.data)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(exc)
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics no instalado: pip install ultralytics")
        return 1

    args.device = resolve_device(args.device)

    try:
        model = YOLO(args.model)
        model.train(
            data=str(Path(args.data).resolve()),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            project=str(RUNS_DIR),
            name="ecosort",
            exist_ok=True,
        )
        best_pt = Path(model.trainer.best)
        best_model = YOLO(str(best_pt))
        metrics = best_model.val(data=str(Path(args.data).resolve()), device=args.device)
    except Exception as exc:
        logger.error("Fallo durante el entrenamiento/validación: %s", exc)
        return 1

    # Copia el mejor modelo a models/best.pt para que app.py lo encuentre
    export_path = None
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        (MODELS_DIR / "best.pt").write_bytes(best_pt.read_bytes())
        export_path = best_model.export(format="ncnn")  # para Raspberry Pi
        logger.info("Modelo NCNN exportado en: %s", export_path)
    except Exception as exc:
        logger.error("Fallo exportando a NCNN (el modelo .pt sí se guardó): %s", exc)

    try:
        write_training_log(metrics, args, export_path, BASE_DIR / "training_log.txt")
        logger.info("Métricas guardadas en training_log.txt")
    except Exception as exc:
        logger.error("No se pudo escribir training_log.txt: %s", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
