"""
layout.py - Disposición física de la estación (medidas en milímetros).

Sistema de coordenadas: origen en el centro de la base del brazo, x hacia
adelante, y a la izquierda, z hacia arriba. Los puntos se dan en polares
(radio en mm, ángulo en grados). AJUSTA estas cifras a tu maqueta real.
"""

import math

TRAY = (140.0, -45.0)          # bandeja de entrada donde se pone el objeto
TABLE_Z = 0.0
OBJECT_Z = 8.0                 # altura del centro del objeto sobre la mesa
GRASP_Z = 15.0                 # altura de la punta al tomar
CARRY_Z = 100.0                # altura de traslado
DROP_Z = 110.0                 # altura sobre el contenedor al soltar
HOME = (100.0, 0.0, 110.0)     # posición de reposo (x, y, z de la punta)

BINS = {
    "reciclable": (160.0, 40.0),
    "papel": (160.0, 80.0),
    "organico": (160.0, 120.0),
    "revision": (150.0, -110.0),
}
BIN_SIZE = 70.0
BIN_HEIGHT = 40.0
TRAY_SIZE = 60.0


def polar_to_xy(r, theta_deg):
    t = math.radians(theta_deg)
    return r * math.cos(t), r * math.sin(t)
