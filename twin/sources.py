"""
sources.py - Fuentes de estado del brazo: demostración, manual y robot por USB.

Todas devuelven un ArmState con los ángulos q1..q5 (ver kinematics.py).

SerialSource es SOLO LECTURA y está pensada para servos de bus tipo Feetech STS.
La dirección del registro de posición (56) y el formato del paquete salen de la
documentación general de esa familia y NO están verificados con tu modelo exacto:
confírmalo en la hoja de datos de tus servos antes de conectarlo.
"""

import json
import math
from dataclasses import dataclass
from typing import Optional

from . import layout
from .fusion import BIN_NAMES, Decision, TactileReading, decide
from .kinematics import ArmGeometry, inverse_kinematics

CYCLE_S = 8.3
T_CLOSE = 2.6      # instante en que la pinza se cierra y se leen los sensores
T_RELEASE = 6.0    # instante en que se suelta el objeto

DEMO_OBJECTS = [
    {"label": "botella de plástico", "cat": "plastic", "conf": 0.93,
     "tactile": TactileReading(65, 18, False, 22)},
    {"label": "lata de aluminio", "cat": "metal", "conf": 0.90,
     "tactile": TactileReading(66, 31, True, 14)},
    {"label": "caja de cartón", "cat": "cardboard", "conf": 0.86,
     "tactile": TactileReading(60, 15, False, 35)},
    {"label": "cáscara de plátano", "cat": "organic", "conf": 0.81,
     "tactile": TactileReading(55, 12, False, 90)},
    {"label": "lata con etiqueta de papel", "cat": "paper", "conf": 0.74,
     "tactile": TactileReading(66, 31, True, 16)},   # trampa: la cámara se equivoca
    {"label": "pila usada", "cat": "electronic", "conf": 0.88,
     "tactile": TactileReading(50, 34, True, 25)},
]


@dataclass
class ArmState:
    q: tuple
    phase: str = ""
    obj_label: str = ""
    obj_xyz: Optional[tuple] = None
    vision_category: str = ""
    vision_conf: float = 0.0
    tactile: Optional[TactileReading] = None
    decision: Optional[Decision] = None
    cycle: int = 0
    source: str = ""
    ok: bool = True
    message: str = ""


def _lerp(a, b, s):
    return a + (b - a) * s


def _polar_xyz(r, theta, z):
    x, y = layout.polar_to_xy(r, theta)
    return x, y, z


class DemoSource:
    """Simula un ciclo de clasificación completo sin necesitar el robot."""

    def __init__(self, geo=None):
        self.geo = geo or ArmGeometry()
        hx, hy, hz = layout.HOME
        self.home = (math.hypot(hx, hy), math.degrees(math.atan2(hy, hx)), hz)

    def _keyframes(self, obj, bin_key):
        tr, tth = layout.TRAY
        br, bth = layout.BINS[bin_key]
        size = obj["tactile"].size_mm
        h = self.home
        return [
            (0.0, h, 60.0, ""),
            (1.0, (tr, tth, layout.CARRY_Z), 60.0, "Moviéndose a la bandeja"),
            (2.0, (tr, tth, layout.GRASP_Z), 60.0, "Bajando a tomar el objeto"),
            (T_CLOSE, (tr, tth, layout.GRASP_Z), size, "Cerrando pinza y leyendo sensores"),
            (3.6, (tr, tth, layout.CARRY_Z), size, "Levantando el objeto"),
            (5.4, (br, bth, layout.DROP_Z), size, "Llevando al contenedor " + BIN_NAMES[bin_key]),
            (T_RELEASE, (br, bth, layout.DROP_Z), 60.0, "Soltando el objeto"),
            (CYCLE_S, h, 60.0, "Volviendo a inicio"),
        ]

    def decision_for(self, index):
        obj = DEMO_OBJECTS[index % len(DEMO_OBJECTS)]
        return obj, decide(obj["cat"], obj["conf"], obj["tactile"])

    def state_at(self, t):
        cycle = int(t // CYCLE_S)
        tt = t - cycle * CYCLE_S
        obj, dec = self.decision_for(cycle)
        kfs = self._keyframes(obj, dec.bin)
        pos, opening, phase = kfs[0][1], kfs[0][2], "Inicio"
        for (t0, p0, o0, _), (t1, p1, o1, name) in zip(kfs, kfs[1:]):
            if t0 <= tt <= t1:
                s = (tt - t0) / (t1 - t0)
                e = (1 - math.cos(math.pi * s)) / 2          # suavizado coseno
                pos = tuple(_lerp(a, b, e) for a, b in zip(p0, p1))
                opening, phase = _lerp(o0, o1, e), name
                break
        xyz = _polar_xyz(*pos)
        q = inverse_kinematics(*xyz, geo=self.geo, gripper=opening)
        if q is None:
            return ArmState((0, 45, -90, -45, opening), phase, ok=False,
                            message="Punto fuera de alcance: ajusta layout.py")

        tr, tth = layout.TRAY
        if tt < T_CLOSE:
            obj_xyz = _polar_xyz(tr, tth, layout.OBJECT_Z)
        elif tt < T_RELEASE:
            obj_xyz = xyz
        else:
            obj_xyz = None
        sensed = tt >= T_CLOSE
        return ArmState(
            q=q, phase=phase, obj_label=obj["label"], obj_xyz=obj_xyz,
            vision_category=obj["cat"], vision_conf=obj["conf"],
            tactile=obj["tactile"] if sensed else None,
            decision=dec if sensed else None, cycle=cycle, source="Demostración",
        )

    def tally(self, t):
        """Cuántos objetos se han depositado en cada contenedor hasta el instante t."""
        counts = {k: 0 for k in BIN_NAMES}
        cycle = int(t // CYCLE_S)
        tt = t - cycle * CYCLE_S
        done = cycle + (1 if tt >= T_RELEASE else 0)
        for i in range(done):
            counts[self.decision_for(i)[1].bin] += 1
        return counts


class ManualSource:
    """Estado definido por los deslizadores de la pantalla."""

    def state(self, q):
        return ArmState(q=tuple(q), phase="Control manual", source="Sliders manuales")


# ---------------------------------------------------------------
# Robot real por USB (solo lectura)
# ---------------------------------------------------------------
def build_read_packet(servo_id, address=56, length=2):
    """Paquete de lectura estilo Feetech: FF FF id len 02 addr n checksum."""
    body = [servo_id, 4, 0x02, address, length]
    return bytes([0xFF, 0xFF] + body + [(~sum(body)) & 0xFF])


def parse_response(data, expected_id):
    """Devuelve la posición (ticks) o None si el paquete es inválido."""
    if len(data) < 8 or data[0] != 0xFF or data[1] != 0xFF or data[2] != expected_id:
        return None
    length = data[3]
    if len(data) < 4 + length or length < 4:
        return None
    if (~sum(data[2:3 + length])) & 0xFF != data[3 + length]:
        return None
    if data[4] != 0:                      # byte de error del servo
        return None
    return data[5] | (data[6] << 8)


def ticks_to_deg(ticks, zero, direction=1):
    """4096 ticks por vuelta (típico de servos STS; verifica el tuyo)."""
    return (ticks - zero) * 360.0 / 4096.0 * direction


def load_calibration(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class SerialSource:
    """Lee las posiciones de los servos y las convierte a ángulos del modelo."""

    def __init__(self, port, calibration):
        import serial  # pyserial, se importa aquí para no exigirlo en modo demo

        self.cal = calibration
        self.ser = serial.Serial(port, calibration.get("baud", 1000000), timeout=0.05)
        self.last_q = (0.0, 45.0, -90.0, -45.0, 60.0)

    def close(self):
        self.ser.close()

    def state(self):
        ids = self.cal["ids"]
        zero, direction = self.cal["zero_ticks"], self.cal["direction"]
        angles, bad = [], []
        for i, sid in enumerate(ids):
            self.ser.reset_input_buffer()
            self.ser.write(build_read_packet(sid, self.cal.get("position_register", 56)))
            ticks = parse_response(self.ser.read(8), sid)
            if ticks is None:
                bad.append(sid)
                angles.append(None)
            else:
                angles.append(ticks_to_deg(ticks, zero[i], direction[i]))
        if bad:
            return ArmState(self.last_q, "Sin respuesta", source="Robot por USB", ok=False,
                            message=f"Sin respuesta de los servos {bad}")
        q1, q2, q3, q4, g = angles
        opening = max(0.0, min(70.0, abs(g) / 90.0 * 60.0))   # mapeo aproximado, calibrar
        self.last_q = (q1, q2, q3, q4, opening)
        return ArmState(self.last_q, "Leyendo robot", source="Robot por USB")
