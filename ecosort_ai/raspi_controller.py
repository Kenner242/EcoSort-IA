"""
raspi_controller.py - Control de contenedores con servomotores en Raspberry Pi.

BinController mueve 3 servos (GPIO 17, 18, 27). RaspiApp captura video,
detecta residuos con el modelo NCNN y abre el contenedor correspondiente.
En PC (sin RPi.GPIO) se usa un mock que solo imprime las acciones.
"""

import logging
import time

import cv2

from config import BIN_OPEN_THRESHOLD, MODEL_PATH, NCNN_MODEL_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# GPIO real o mock (para probar en PC)
# ---------------------------------------------------------------
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

    class _MockPWM:
        """PWM simulado."""
        def __init__(self, pin, freq):
            self.pin = pin

        def start(self, duty):
            print(f"[MOCK] PWM pin {self.pin} start duty={duty}")

        def ChangeDutyCycle(self, duty):
            print(f"[MOCK] PWM pin {self.pin} duty={duty}")

        def stop(self):
            print(f"[MOCK] PWM pin {self.pin} stop")

    class GPIO:  # type: ignore[no-redef]
        """Mock mínimo de RPi.GPIO."""
        BCM = "BCM"
        OUT = "OUT"

        @staticmethod
        def setmode(mode): print(f"[MOCK] setmode({mode})")

        @staticmethod
        def setwarnings(flag): pass

        @staticmethod
        def setup(pin, mode): print(f"[MOCK] setup({pin}, {mode})")

        @staticmethod
        def PWM(pin, freq): return _MockPWM(pin, freq)

        @staticmethod
        def cleanup(): print("[MOCK] cleanup()")

# Servos: GPIO -> contenedor
SERVO_PINS = {"recyclable": 17, "paper": 18, "organic": 27}

# Clase detectada -> contenedor
CLASS_TO_BIN = {
    "plastic": "recyclable",
    "metal": "recyclable",
    "glass": "recyclable",
    "paper": "paper",
    "cardboard": "paper",
    "organic": "organic",
    "trash": "organic",
}

SERVO_FREQ_HZ = 50
ANGLE_CLOSED = 0
ANGLE_OPEN = 90
OPEN_SECONDS = 2.0


def angle_to_duty(angle):
    """Convierte un ángulo (0-180°) a ciclo de trabajo PWM para servos SG90 típicos."""
    return 2.5 + (float(angle) / 180.0) * 10.0


class BinController:
    """Controla 3 servos que abren los contenedores."""

    def __init__(self, pins=None):
        self.pins = dict(pins or SERVO_PINS)
        self.pwm = {}
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            for name, pin in self.pins.items():
                GPIO.setup(pin, GPIO.OUT)
                servo = GPIO.PWM(pin, SERVO_FREQ_HZ)
                servo.start(angle_to_duty(ANGLE_CLOSED))
                self.pwm[name] = servo
            time.sleep(0.5)
            self._release_all()
        except Exception as exc:
            logger.error("Error inicializando GPIO: %s", exc)
            raise

    def _release_all(self):
        """Duty 0 para evitar vibración (jitter) de los servos en reposo."""
        for servo in self.pwm.values():
            servo.ChangeDutyCycle(0)

    def open_bin(self, class_name):
        """Abre el contenedor de la clase durante 2 s y lo vuelve a cerrar."""
        bin_name = CLASS_TO_BIN.get(str(class_name).lower())
        if bin_name is None or bin_name not in self.pwm:
            logger.warning("Clase sin contenedor asignado: %s", class_name)
            return False
        servo = self.pwm[bin_name]
        try:
            logger.info("Abriendo contenedor '%s' (%s)", bin_name, class_name)
            servo.ChangeDutyCycle(angle_to_duty(ANGLE_OPEN))
            time.sleep(OPEN_SECONDS)
            servo.ChangeDutyCycle(angle_to_duty(ANGLE_CLOSED))
            time.sleep(0.5)
            servo.ChangeDutyCycle(0)
            return True
        except Exception as exc:
            logger.error("Error moviendo servo: %s", exc)
            return False

    def cleanup(self):
        """Detiene los PWM y libera los pines GPIO."""
        try:
            for servo in self.pwm.values():
                servo.stop()
            GPIO.cleanup()
        except Exception as exc:
            logger.error("Error en cleanup: %s", exc)


class RaspiApp:
    """Bucle principal: cámara -> detección -> apertura de contenedor."""

    def __init__(self, camera_index=0, cooldown=5.0):
        from detector import WasteDetector  # import tardío: acelera el arranque de las pruebas de GPIO

        model = NCNN_MODEL_PATH if NCNN_MODEL_PATH.exists() else MODEL_PATH
        self.detector = WasteDetector(str(model))
        self.controller = BinController()
        self.camera_index = camera_index
        self.cooldown = cooldown
        self.cap = None

    def run(self):
        """Ejecuta el bucle hasta Ctrl+C."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                logger.error("No se pudo abrir la cámara %s", self.camera_index)
                return
            logger.info("EcoSort en marcha. Ctrl+C para salir.")
            last_open = 0.0
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    logger.warning("Frame no disponible, reintentando...")
                    time.sleep(0.5)
                    continue
                detections = self.detector.detect(frame)
                if detections and time.time() - last_open >= self.cooldown:
                    best = max(detections, key=lambda d: d["confidence"])
                    if best["confidence"] > BIN_OPEN_THRESHOLD:
                        if self.controller.open_bin(best["class_name"]):
                            last_open = time.time()
        except KeyboardInterrupt:
            logger.info("Interrumpido por el usuario.")
        except Exception as exc:
            logger.error("Error en el bucle principal: %s", exc)
        finally:
            self.cleanup()

    def cleanup(self):
        """Libera cámara y GPIO."""
        if self.cap is not None:
            self.cap.release()
        self.controller.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("GPIO real disponible:", GPIO_AVAILABLE)
    RaspiApp().run()
