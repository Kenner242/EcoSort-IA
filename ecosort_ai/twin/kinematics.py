"""
kinematics.py - Cinemática directa e inversa del brazo (5 grados de libertad).

Convención (grados):
  q1  giro de la base (0 = hacia adelante, positivo hacia la izquierda)
  q2  hombro: ángulo del brazo superior sobre la horizontal (90 = vertical)
  q3  codo: ángulo relativo del antebrazo respecto al brazo superior
  q4  muñeca: ángulo relativo de la pinza respecto al antebrazo
  q5  apertura de la pinza en mm

Con la herramienta apuntando hacia abajo, el ángulo absoluto de la pinza es -90.
Las longitudes son de ejemplo: cámbialas por las de tu brazo (ArmGeometry).
"""

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class ArmGeometry:
    base_h: float = 60.0
    upper: float = 110.0
    fore: float = 110.0
    grip: float = 60.0
    limits: tuple = ((-180, 180), (-10, 130), (-150, 150), (-150, 150), (0, 70))


def forward_kinematics(q, geo=None):
    """Devuelve los puntos (np.array de 3) de cada articulación y de los dedos."""
    geo = geo or ArmGeometry()
    q1, q2, q3, q4, q5 = q
    a1 = math.radians(q2)
    a2 = a1 + math.radians(q3)
    a3 = a2 + math.radians(q4)
    yaw = math.radians(q1)

    def to3(r, z):
        return np.array([r * math.cos(yaw), r * math.sin(yaw), z])

    sh = (0.0, geo.base_h)
    el = (sh[0] + geo.upper * math.cos(a1), sh[1] + geo.upper * math.sin(a1))
    wr = (el[0] + geo.fore * math.cos(a2), el[1] + geo.fore * math.sin(a2))
    tip = (wr[0] + geo.grip * math.cos(a3), wr[1] + geo.grip * math.sin(a3))

    tangent = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
    tip3 = to3(*tip)
    half = max(q5, 0.0) / 2.0
    return {
        "base": np.array([0.0, 0.0, 0.0]),
        "shoulder": to3(*sh),
        "elbow": to3(*el),
        "wrist": to3(*wr),
        "tip": tip3,
        "finger_l": tip3 + tangent * half,
        "finger_r": tip3 - tangent * half,
    }


def inverse_kinematics(x, y, z, geo=None, gripper=0.0):
    """Ángulos (q1..q5) para que la punta llegue a (x, y, z) apuntando hacia abajo.

    Solución codo arriba. Devuelve None si el punto es inalcanzable o viola límites.
    """
    geo = geo or ArmGeometry()
    q1 = math.degrees(math.atan2(y, x))
    r = math.hypot(x, y)
    wr, wz = r, z + geo.grip            # la muñeca queda 'grip' por encima de la punta
    dr, dz = wr - 0.0, wz - geo.base_h
    d = math.hypot(dr, dz)
    u, f = geo.upper, geo.fore
    if d > u + f - 1e-6 or d < abs(u - f) + 1e-6:
        return None
    cos_b = (u * u + d * d - f * f) / (2 * u * d)
    a1 = math.atan2(dz, dr) + math.acos(max(-1.0, min(1.0, cos_b)))
    er, ez = u * math.cos(a1), geo.base_h + u * math.sin(a1)
    a2 = math.atan2(wz - ez, wr - er)
    q2 = math.degrees(a1)
    q3 = math.degrees(a2 - a1)
    q4 = -90.0 - math.degrees(a2)
    q = (q1, q2, q3, q4, gripper)
    for value, (lo, hi) in zip(q, geo.limits):
        if not lo - 1e-6 <= value <= hi + 1e-6:
            return None
    return q
