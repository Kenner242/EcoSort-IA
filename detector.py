"""
detector.py - Detección de objetos y residuos con YOLOv8 / YOLO-World, todo en español.

WasteDetector elige automáticamente el mejor modelo disponible:
  1) "trained": models/best.pt (entrenado con tus residuos)  -> más preciso
  2) "world"  : YOLO-World, vocabulario abierto de ~45 residuos y objetos
  3) "coco"   : modelo general de 80 objetos (siempre disponible)
Cada detección trae nombre en español, categoría de residuo y si cuenta como residuo.
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import (
    CLASS_NAMES_ES,
    DETECTION_MODE,
    FALLBACK_MODEL,
    MODE_THRESHOLDS,
    MODEL_PATH,
    POINTS_SYSTEM,
    POINTS_THRESHOLD,
    WORLD_MODEL,
    WORLD_VOCAB,
    resolve_label,
)

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None

logger = logging.getLogger(__name__)

MODE_DESCRIPTIONS = {
    "trained": "Modelo entrenado en residuos",
    "world": "Vocabulario abierto (YOLO-World)",
    "coco": "Modelo general (80 objetos comunes)",
}

# Colores de las cajas (RGB) según la categoría
COLOR_WASTE = (46, 160, 67)
COLOR_ELECTRONIC = (230, 140, 20)
COLOR_NONE = (130, 130, 130)


def _load_font(size):
    """Carga una fuente TrueType con soporte de tildes y ñ; si no hay, usa la básica."""
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_detections(image_bgr, detections):
    """Dibuja cajas y etiquetas en español (con tildes) sobre la imagen. Devuelve BGR."""
    pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    font = _load_font(max(14, pil.width // 40))
    thickness = max(2, pil.width // 300)
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        if det["category"] == "electronic":
            color = COLOR_ELECTRONIC
        elif det["is_waste"]:
            color = COLOR_WASTE
        else:
            color = COLOR_NONE
        draw.rectangle([x1, y1, x2, y2], outline=color, width=thickness)
        text = f"{det['label_es']} {det['confidence']:.0%}"
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        tw, th = right - left, bottom - top
        ty = max(0, y1 - th - 8)
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 8], fill=color)
        draw.text((x1 + 4, ty + 2), text, fill=(255, 255, 255), font=font)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


class WasteDetector:
    """Detector de objetos y residuos con etiquetas en español."""

    def __init__(self, model_path=None, conf=None, mode=None, model=None):
        """Carga el mejor modelo disponible.

        Args:
            model_path: ruta a un modelo entrenado (.pt o carpeta NCNN). Si no existe
                se usa YOLO-World o el modelo general.
            conf: confianza mínima para mostrar (si None, depende del modo).
            mode: "auto" | "world" | "coco" (si None usa DETECTION_MODE de config.py).
            model: modelo ya cargado (para pruebas automáticas).
        """
        self.model = None
        self.mode = None
        self.model_source = None
        if model is not None:
            self.model, self.mode = model, "trained"
        else:
            self._load_best_model(model_path, mode or DETECTION_MODE)
        default_conf, self.points_threshold = MODE_THRESHOLDS.get(self.mode, (0.5, POINTS_THRESHOLD))
        self.conf = conf if conf is not None else default_conf

    # ------------------------------------------------------------------
    # Carga de modelo
    # ------------------------------------------------------------------
    def _load_best_model(self, model_path, wanted_mode):
        """Intenta: entrenado -> YOLO-World -> COCO. Registra qué se usó."""
        if YOLO is None:
            logger.error("ultralytics no está instalado (pip install ultralytics)")
            return

        path = Path(model_path) if model_path else MODEL_PATH
        if path.exists():
            try:
                self.model, self.mode, self.model_source = YOLO(str(path)), "trained", str(path)
                logger.info("Modelo entrenado cargado: %s", path)
                return
            except Exception as exc:
                logger.error("No se pudo cargar %s: %s", path, exc)

        if wanted_mode in ("auto", "world"):
            try:
                from ultralytics import YOLOWorld
                world = YOLOWorld(WORLD_MODEL)
                world.set_classes(WORLD_VOCAB)
                self.model, self.mode, self.model_source = world, "world", WORLD_MODEL
                logger.info("YOLO-World cargado con %d términos", len(WORLD_VOCAB))
                return
            except Exception as exc:
                logger.warning("YOLO-World no disponible (%s). Se usa el modelo general.", exc)

        try:
            self.model, self.mode, self.model_source = YOLO(FALLBACK_MODEL), "coco", FALLBACK_MODEL
            logger.info("Modelo general cargado: %s", FALLBACK_MODEL)
        except Exception as exc:
            logger.error("No se pudo cargar ningún modelo: %s", exc)
            self.model = None

    @property
    def mode_description(self):
        """Descripción en español del modo activo."""
        return MODE_DESCRIPTIONS.get(self.mode, "Sin modelo cargado")

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    @staticmethod
    def _prepare_image(image):
        """Convierte la entrada (ndarray BGR, PIL o ruta) a ndarray BGR. Devuelve None si es inválida."""
        try:
            if image is None:
                return None
            if isinstance(image, (str, Path)):
                return cv2.imread(str(image))
            if isinstance(image, Image.Image):
                return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
            if isinstance(image, np.ndarray):
                if image.size == 0:
                    return None
                if image.ndim == 2:
                    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                return image
        except Exception as exc:
            logger.error("Error preparando la imagen: %s", exc)
        return None

    def _predict(self, image):
        """Ejecuta la inferencia. Devuelve (imagen_bgr | None, lista_de_detecciones)."""
        arr = self._prepare_image(image)
        if arr is None or self.model is None:
            return arr, []
        try:
            result = self.model.predict(source=arr, conf=self.conf, verbose=False)[0]
            detections = []
            for box in result.boxes:
                label_en = str(result.names[int(box.cls[0])])
                label_es, category = resolve_label(label_en)
                detections.append({
                    "class_name": category,                 # categoría interna (para puntos y contenedores)
                    "category": category,
                    "label_en": label_en,
                    "label_es": label_es,                   # nombre en español del objeto
                    "category_es": CLASS_NAMES_ES.get(category, category),
                    "is_waste": category in POINTS_SYSTEM,  # True si es un residuo clasificable
                    "confidence": float(box.conf[0]),
                    "bbox": [float(v) for v in box.xyxy[0].tolist()],
                })
            detections.sort(key=lambda d: d["confidence"], reverse=True)
            return arr, detections
        except Exception as exc:
            logger.error("Error durante la inferencia: %s", exc)
            return arr, []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def detect(self, image):
        """Detecta objetos/residuos en una imagen.

        Returns:
            list[dict]: cada elemento trae class_name (categoría), label_es, label_en,
            category_es, is_waste, confidence y bbox. Lista vacía si la imagen es
            None/inválida o no hay detecciones.
        """
        try:
            _, detections = self._predict(image)
            return detections
        except Exception as exc:
            logger.error("Error en detect(): %s", exc)
            return []

    def detect_from_frame(self, frame):
        """Detecta sobre un frame y dibuja las etiquetas en español.

        Returns:
            tuple: (imagen_anotada_BGR, lista_de_detecciones). Si falla, devuelve el
            frame original (o None) y una lista vacía.
        """
        try:
            arr, detections = self._predict(frame)
            if arr is None:
                return frame, []
            return draw_detections(arr, detections), detections
        except Exception as exc:
            logger.error("Error en detect_from_frame(): %s", exc)
            return frame, []

    @staticmethod
    def get_points_for_detection(class_name, confidence, threshold=None):
        """Calcula los Eco-Puntos de una detección.

        Solo otorga puntos si confidence >= threshold (por defecto POINTS_THRESHOLD)
        y la categoría es un residuo con puntos; de lo contrario devuelve 0.
        """
        try:
            limit = POINTS_THRESHOLD if threshold is None else threshold
            if confidence is None or float(confidence) < limit:
                return 0
            return int(POINTS_SYSTEM.get(str(class_name).strip().lower(), 0))
        except Exception as exc:
            logger.error("Error calculando puntos: %s", exc)
            return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = WasteDetector(str(MODEL_PATH))
    print("Modo activo:", detector.mode_description)
    blank = np.full((640, 640, 3), 255, dtype=np.uint8)
    print("Detecciones en imagen en blanco:", detector.detect(blank))
    annotated, dets = detector.detect_from_frame(blank)
    print("Frame anotado:", None if annotated is None else annotated.shape, "| detecciones:", dets)
    print("Puntos Plástico@0.9:", detector.get_points_for_detection("plastic", 0.9))
    print("Puntos Plástico@0.6:", detector.get_points_for_detection("plastic", 0.6))
