"""
test_detector.py - Pruebas automatizadas de EcoSort AI.

Ejecutar con:  pytest -v test_detector.py

Las pruebas con modelo falso (FakeModel) no necesitan internet ni descargar nada.
Las pruebas con modelo real se omiten automáticamente si no se puede cargar.
"""

import numpy as np
import pytest

from config import MODEL_PATH, POINTS_SYSTEM, POINTS_THRESHOLD, display_name, resolve_label
from detector import WasteDetector, draw_detections
from gamification import EcoPointsManager


# ---------------------------------------------------------------
# Modelo falso para pruebas rápidas y deterministas
# ---------------------------------------------------------------
class _Val:
    """Imita un tensor mínimo: soporta [0], float(), int() y tolist()."""
    def __init__(self, value):
        self.value = value

    def __getitem__(self, _):
        return self.value

    def tolist(self):
        return list(self.value)


class _Arr:
    """Imita un vector de coordenadas con método tolist()."""
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return list(self.values)


class _Box:
    def __init__(self, cls_id, conf, xyxy):
        self.cls, self.conf, self.xyxy = _Val(cls_id), _Val(conf), _Val(_Arr(xyxy))


class _Result:
    def __init__(self, names, boxes):
        self.names, self.boxes = names, boxes


class FakeModel:
    """Devuelve siempre las mismas cajas, como si fuera YOLO."""
    def __init__(self, names, boxes):
        self._result = _Result(names, boxes)

    def predict(self, source, conf, verbose):
        return [self._result]


@pytest.fixture
def fake_detector():
    names = {0: "bottle", 1: "person", 2: "remote"}
    boxes = [
        _Box(0, 0.88, [10, 10, 100, 200]),
        _Box(1, 0.95, [150, 20, 300, 300]),
        _Box(2, 0.60, [320, 40, 380, 120]),
    ]
    return WasteDetector(model=FakeModel(names, boxes))


# ---------------------------------------------------------------
# Pruebas con modelo falso
# ---------------------------------------------------------------
def test_detections_are_in_spanish(fake_detector):
    image = np.full((400, 400, 3), 255, dtype=np.uint8)
    dets = fake_detector.detect(image)
    by_en = {d["label_en"]: d for d in dets}
    assert by_en["bottle"]["label_es"] == "botella" and by_en["bottle"]["is_waste"] is True
    assert by_en["person"]["label_es"] == "persona" and by_en["person"]["is_waste"] is False
    assert by_en["remote"]["category"] == "electronic" and by_en["remote"]["is_waste"] is False
    assert dets[0]["confidence"] >= dets[-1]["confidence"]  # ordenadas de mayor a menor


def test_draw_detections_keeps_shape(fake_detector):
    image = np.full((400, 400, 3), 255, dtype=np.uint8)
    annotated, dets = fake_detector.detect_from_frame(image)
    assert annotated.shape == image.shape
    assert len(dets) == 3
    assert not np.array_equal(annotated, image)  # se dibujó algo


def test_resolve_label_spanish_and_unknown():
    assert resolve_label("plastic bottle") == ("botella de plástico", "plastic")
    assert resolve_label("vidrio") == ("Vidrio", "glass")
    assert resolve_label("Cartón")[1] == "cardboard"
    assert resolve_label("objeto raro")[1] == "none"
    assert display_name("plastic") == "Plástico"


# ---------------------------------------------------------------
# Pruebas con modelo real (se omiten si no hay modelo/internet)
# ---------------------------------------------------------------
@pytest.fixture(scope="module")
def detector():
    pytest.importorskip("ultralytics")
    det = WasteDetector(str(MODEL_PATH))
    if det.model is None:
        pytest.skip("No se pudo cargar ningún modelo (¿sin internet para descargarlo?)")
    return det


def test_detect_blank_image(detector):
    blank = np.full((640, 640, 3), 255, dtype=np.uint8)
    result = detector.detect(blank)
    assert isinstance(result, list)
    assert all(d["confidence"] < 0.5 for d in result)  # una imagen en blanco no debe dar detecciones seguras


def test_detect_none_image(detector):
    assert detector.detect(None) == []


def test_detect_none_without_model():
    assert WasteDetector(model=FakeModel({}, [])).detect(None) == []


# ---------------------------------------------------------------
# Puntos y gamificación
# ---------------------------------------------------------------
def test_points_below_threshold():
    assert WasteDetector.get_points_for_detection("plastic", POINTS_THRESHOLD - 0.01) == 0
    assert WasteDetector.get_points_for_detection("plastic", 0.95) == POINTS_SYSTEM["plastic"]
    assert WasteDetector.get_points_for_detection("none", 0.99) == 0
    assert WasteDetector.get_points_for_detection("plastic", 0.40, threshold=0.35) == POINTS_SYSTEM["plastic"]


def test_gamification_flow(tmp_path):
    manager = EcoPointsManager(tmp_path / "test.db")
    user_id = manager.get_or_create_user("tester")
    assert manager.get_or_create_user("tester") == user_id  # no duplica usuarios

    manager.add_scan(user_id, "plastic", 150, 0.9, "h1")
    manager.add_scan(user_id, "metal", 200, 0.85, "h2")
    manager.add_scan(user_id, "paper", 100, 0.8, "h3")

    assert manager.get_user_points(user_id) == 450
    assert manager.is_duplicate_scan("h1", user_id) is True
    assert manager.is_duplicate_scan("otro", user_id) is False
    assert manager.get_user_badge(user_id) == "Reciclador Novato"
    assert len(manager.get_user_history(user_id, limit=5)) == 3
    assert manager.get_leaderboard()[0]["username"] == "tester"


def test_impact_metrics(tmp_path):
    from impact import compute_impact

    result = compute_impact({"plastic": 10, "metal": 10, "trash": 10})
    assert result["items"] == 30
    assert result["kg_trash"] == pytest.approx(0.5)
    assert 0 < result["diversion_rate"] < 1
    assert result["co2e_avoided"] > 0
    assert compute_impact({})["diversion_rate"] == 0.0

    manager = EcoPointsManager(tmp_path / "impact.db")
    a, b = manager.get_or_create_user("a"), manager.get_or_create_user("b")
    manager.add_scan(a, "plastic", 150, 0.9, "x1")
    manager.add_scan(a, "plastic", 150, 0.9, "x2")
    manager.add_scan(b, "metal", 200, 0.9, "x3")
    assert manager.get_category_counts(a) == {"plastic": 2}
    assert manager.get_category_counts() == {"plastic": 2, "metal": 1}
