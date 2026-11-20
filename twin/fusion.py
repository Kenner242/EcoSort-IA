"""
fusion.py - Fusión de visión y tacto para decidir a dónde va cada residuo.

Regla: la cámara propone una categoría con una confianza; el tacto la confirma
o la contradice. Si no coinciden, el objeto va a revisión humana en vez de
contaminar un contenedor. Los umbrales son PROPUESTAS que hay que validar con
pruebas reales.
"""

from dataclasses import dataclass

CONF_MIN = 0.60

BIN_NAMES = {
    "reciclable": "Reciclables",
    "papel": "Papel y cartón",
    "organico": "Orgánicos",
    "revision": "Revisión humana",
}

BIN_FOR_CATEGORY = {
    "plastic": "reciclable",
    "metal": "reciclable",
    "glass": "reciclable",
    "paper": "papel",
    "cardboard": "papel",
    "organic": "organico",
    "trash": "revision",
}


@dataclass
class TactileReading:
    size_mm: float        # ancho medido por la apertura de la pinza
    current_ma: float     # corriente del servo al apretar (rigidez)
    is_metal: bool        # sensor inductivo
    weight_g: float       # celda de carga


@dataclass
class Decision:
    action: str           # depositar | revisar | ignorar
    bin: str              # clave de BIN_NAMES
    reason: str


def decide(category, confidence, tactile=None):
    """Decide la acción final a partir de la visión y el tacto."""
    if category in (None, "", "none"):
        return Decision("ignorar", "revision", "No se reconoce un residuo.")
    if category == "electronic":
        return Decision("revisar", "revision", "Residuo electrónico: llevar a punto limpio, no a reciclables.")
    if confidence < CONF_MIN:
        return Decision("revisar", "revision", f"Confianza baja de la cámara ({confidence:.0%}).")
    if tactile is not None:
        if tactile.is_metal and category != "metal":
            return Decision("revisar", "revision",
                            f"La cámara dice {category} pero el sensor detecta metal: posible contaminación.")
        if category == "metal" and not tactile.is_metal:
            return Decision("revisar", "revision", "La cámara dice metal pero el sensor no lo confirma.")
    bin_key = BIN_FOR_CATEGORY.get(category, "revision")
    if bin_key == "revision":
        return Decision("depositar", "revision", "No aprovechable: contenedor de no reciclables.")
    return Decision("depositar", bin_key, "Visión y tacto coinciden.")
