"""
config.py - Configuración central de EcoSort AI.

Define rutas, sistema de puntos, umbrales, catálogo de objetos en español
(nombre + categoría de residuo) e insignias. Todos los módulos importan de aquí.
"""

from pathlib import Path

# ---------------------------------------------------------------
# Rutas (todas relativas a la carpeta del proyecto)
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "best.pt"                    # modelo entrenado en residuos (PyTorch)
NCNN_MODEL_PATH = MODELS_DIR / "best_ncnn_model"       # modelo exportado para Raspberry Pi
DB_PATH = BASE_DIR / "ecosort.db"                      # base de datos SQLite
DATASET_PATH = BASE_DIR / "dataset"
DATA_YAML_PATH = BASE_DIR / "data.yaml"
RUNS_DIR = BASE_DIR / "runs"

# ---------------------------------------------------------------
# Modo de detección
#   "auto"  : usa models/best.pt si existe; si no, intenta YOLO-World
#             (vocabulario abierto: reconoce muchos residuos sin entrenar);
#             si eso falla, usa el modelo general COCO (80 objetos).
#   "world" : fuerza YOLO-World.   "coco": fuerza el modelo general.
# ---------------------------------------------------------------
DETECTION_MODE = "auto"
WORLD_MODEL = "yolov8s-worldv2.pt"   # se descarga solo la primera vez (~25 MB)
FALLBACK_MODEL = "yolov8s.pt"        # modelo general COCO (se descarga solo)

# (confianza mínima para mostrar, confianza mínima para dar puntos) según el modo.
# YOLO-World entrega confianzas más bajas, por eso sus umbrales son menores.
MODE_THRESHOLDS = {
    "trained": (0.50, 0.70),
    "world": (0.20, 0.35),
    "coco": (0.40, 0.60),
}

# ---------------------------------------------------------------
# Sistema de puntos (Eco-Puntos por tipo de residuo)
# ---------------------------------------------------------------
POINTS_SYSTEM = {
    "plastic": 150,
    "metal": 200,
    "glass": 120,
    "paper": 100,
    "organic": 80,
    "cardboard": 100,
    "trash": 5,
}

# Umbrales para el modelo entrenado (valores por defecto)
CONFIDENCE_THRESHOLD = 0.5   # confianza mínima para reportar una detección
POINTS_THRESHOLD = 0.7       # confianza mínima para otorgar puntos
BIN_OPEN_THRESHOLD = 0.75    # confianza mínima para abrir un contenedor (Raspberry Pi)

# Clases del modelo entrenado (deben coincidir con 'names' de data.yaml)
CLASSES = ["plastic", "metal", "glass", "paper", "organic", "cardboard", "trash"]

# ---------------------------------------------------------------
# Nombres en español de las categorías (claves internas en inglés)
# ---------------------------------------------------------------
CLASS_NAMES_ES = {
    "plastic": "Plástico",
    "metal": "Metal",
    "glass": "Vidrio",
    "paper": "Papel",
    "organic": "Orgánico",
    "cardboard": "Cartón",
    "trash": "Basura general",
    "electronic": "Residuo electrónico (punto limpio)",
    "none": "No es un residuo",
}

# Si tu dataset está etiquetado en español, estas etiquetas se convierten a las claves internas.
SPANISH_ALIASES = {
    "plastico": "plastic", "plástico": "plastic",
    "metal": "metal",
    "vidrio": "glass",
    "papel": "paper",
    "organico": "organic", "orgánico": "organic", "organica": "organic", "orgánica": "organic",
    "carton": "cardboard", "cartón": "cardboard",
    "basura": "trash",
}
CLASS_ALIASES = dict(SPANISH_ALIASES)

# ---------------------------------------------------------------
# Catálogo de objetos: etiqueta en inglés -> (nombre en español, categoría)
# 1) Los 80 objetos del modelo COCO
# ---------------------------------------------------------------
OBJECT_CATALOG = {
    # Personas, vehículos y entorno (no son residuos)
    "person": ("persona", "none"), "bicycle": ("bicicleta", "none"), "car": ("auto", "none"),
    "motorcycle": ("motocicleta", "none"), "airplane": ("avión", "none"), "bus": ("bus", "none"),
    "train": ("tren", "none"), "truck": ("camión", "none"), "boat": ("bote", "none"),
    "traffic light": ("semáforo", "none"), "fire hydrant": ("grifo de incendio", "none"),
    "stop sign": ("señal de pare", "none"), "parking meter": ("parquímetro", "none"),
    "bench": ("banca", "none"),
    # Animales
    "bird": ("pájaro", "none"), "cat": ("gato", "none"), "dog": ("perro", "none"),
    "horse": ("caballo", "none"), "sheep": ("oveja", "none"), "cow": ("vaca", "none"),
    "elephant": ("elefante", "none"), "bear": ("oso", "none"), "zebra": ("cebra", "none"),
    "giraffe": ("jirafa", "none"),
    # Accesorios y deportes
    "backpack": ("mochila", "none"), "umbrella": ("paraguas", "none"), "handbag": ("cartera", "none"),
    "tie": ("corbata", "none"), "suitcase": ("maleta", "none"), "frisbee": ("frisbee", "none"),
    "skis": ("esquís", "none"), "snowboard": ("snowboard", "none"), "sports ball": ("pelota", "none"),
    "kite": ("volantín", "none"), "baseball bat": ("bate de béisbol", "none"),
    "baseball glove": ("guante de béisbol", "none"), "skateboard": ("skate", "none"),
    "surfboard": ("tabla de surf", "none"), "tennis racket": ("raqueta de tenis", "none"),
    # Cocina y comida
    "bottle": ("botella", "plastic"), "wine glass": ("copa de vidrio", "glass"),
    "cup": ("vaso o taza", "paper"), "fork": ("tenedor", "metal"), "knife": ("cuchillo", "metal"),
    "spoon": ("cuchara", "metal"), "bowl": ("bol", "trash"),
    "banana": ("plátano", "organic"), "apple": ("manzana", "organic"), "sandwich": ("sándwich", "organic"),
    "orange": ("naranja", "organic"), "broccoli": ("brócoli", "organic"), "carrot": ("zanahoria", "organic"),
    "hot dog": ("completo/hot dog", "organic"), "pizza": ("pizza", "organic"),
    "donut": ("dona", "organic"), "cake": ("torta", "organic"),
    # Hogar y muebles (no son residuos de este contenedor)
    "chair": ("silla", "none"), "couch": ("sofá", "none"), "potted plant": ("planta", "organic"),
    "bed": ("cama", "none"), "dining table": ("mesa", "none"), "toilet": ("inodoro", "none"),
    "microwave": ("microondas", "none"), "oven": ("horno", "none"), "toaster": ("tostador", "none"),
    "sink": ("lavaplatos", "none"), "refrigerator": ("refrigerador", "none"),
    "clock": ("reloj", "none"), "vase": ("florero", "glass"), "teddy bear": ("peluche", "trash"),
    # Electrónicos (requieren punto limpio)
    "tv": ("televisor", "electronic"), "laptop": ("computador portátil", "electronic"),
    "mouse": ("mouse de computador", "electronic"), "remote": ("control remoto", "electronic"),
    "keyboard": ("teclado", "electronic"), "cell phone": ("teléfono celular", "electronic"),
    "hair drier": ("secador de pelo", "electronic"),
    # Otros
    "book": ("libro", "paper"), "scissors": ("tijeras", "metal"),
    "toothbrush": ("cepillo de dientes", "trash"),
}

# 2) Vocabulario de residuos para el modo YOLO-World (tupla: prompt en inglés, español, categoría)
WORLD_ITEMS = [
    # Plástico
    ("plastic bottle", "botella de plástico", "plastic"),
    ("shampoo bottle", "envase de shampoo", "plastic"),
    ("plastic container", "envase plástico", "plastic"),
    ("plastic bag", "bolsa plástica", "plastic"),
    ("plastic cup", "vaso plástico", "plastic"),
    ("plastic wrapper", "envoltorio plástico", "plastic"),
    ("drinking straw", "bombilla (pajita)", "plastic"),
    # Metal
    ("aluminum can", "lata de aluminio", "metal"),
    ("soda can", "lata de bebida", "metal"),
    ("tin can", "lata de conserva", "metal"),
    ("aerosol can", "aerosol", "metal"),
    ("aluminum foil", "papel aluminio", "metal"),
    # Vidrio
    ("glass bottle", "botella de vidrio", "glass"),
    ("glass jar", "frasco de vidrio", "glass"),
    ("broken glass", "vidrio roto", "glass"),
    # Papel y cartón
    ("newspaper", "periódico", "paper"),
    ("paper sheet", "hoja de papel", "paper"),
    ("paper bag", "bolsa de papel", "paper"),
    ("paper cup", "vaso de papel", "paper"),
    ("magazine", "revista", "paper"),
    ("cardboard box", "caja de cartón", "cardboard"),
    ("milk carton", "envase de cartón (leche o jugo)", "cardboard"),
    ("egg carton", "cartón de huevos", "cardboard"),
    # Orgánico
    ("banana peel", "cáscara de plátano", "organic"),
    ("apple core", "corazón de manzana", "organic"),
    ("food scraps", "restos de comida", "organic"),
    ("egg shell", "cáscara de huevo", "organic"),
    ("fruit", "fruta", "organic"),
    ("vegetable", "verdura", "organic"),
    # Basura general
    ("styrofoam", "plumavit (poliestireno)", "trash"),
    ("cigarette butt", "colilla de cigarro", "trash"),
    ("diaper", "pañal", "trash"),
    ("old clothes", "ropa usada", "trash"),
    # Electrónicos
    ("battery", "pila o batería", "electronic"),
    ("light bulb", "ampolleta", "electronic"),
    ("headphones", "audífonos", "electronic"),
    ("cell phone", "teléfono celular", "electronic"),
    ("laptop", "computador portátil", "electronic"),
    # Cosas que NO son residuos (evitan que el modelo fuerce una etiqueta de residuo)
    ("person", "persona", "none"),
    ("hand", "mano", "none"),
    ("face", "rostro", "none"),
    ("table", "mesa", "none"),
    ("chair", "silla", "none"),
]
WORLD_VOCAB = [item[0] for item in WORLD_ITEMS]
for _en, _es, _cat in WORLD_ITEMS:
    OBJECT_CATALOG[_en] = (_es, _cat)

# ---------------------------------------------------------------
# Funciones de apoyo
# ---------------------------------------------------------------
def resolve_label(label):
    """Convierte una etiqueta del modelo (en inglés o español) a (nombre_es, categoría).

    Orden: categoría interna -> alias en español -> catálogo de objetos -> desconocida.
    Una etiqueta desconocida se muestra tal cual y se trata como 'none' (sin puntos).
    """
    key = str(label).strip().lower()
    if key in CLASS_NAMES_ES and key not in ("none", "electronic"):
        return CLASS_NAMES_ES[key], key
    if key in SPANISH_ALIASES:
        cat = SPANISH_ALIASES[key]
        return CLASS_NAMES_ES[cat], cat
    if key in OBJECT_CATALOG:
        return OBJECT_CATALOG[key]
    return str(label).strip().capitalize(), "none"


def display_name(class_name):
    """Nombre en español de una categoría interna ('plastic' -> 'Plástico') o de una etiqueta."""
    key = str(class_name).strip().lower()
    if key in CLASS_NAMES_ES:
        return CLASS_NAMES_ES[key]
    return resolve_label(key)[0]

# ---------------------------------------------------------------
# Insignias: nombre -> puntos mínimos necesarios
# ---------------------------------------------------------------
BADGES = {
    "Reciclador Novato": 100,
    "Eco-Héroe": 1000,
    "Guardián del Planeta": 5000,
}

# Ventana (horas) en la que una misma imagen cuenta como duplicada
DUPLICATE_WINDOW_HOURS = 24


if __name__ == "__main__":
    print("Objetos en el catálogo:", len(OBJECT_CATALOG))
    print("Vocabulario YOLO-World:", len(WORLD_VOCAB), "términos")
    for test in ("bottle", "plastic bottle", "remote", "vidrio", "algo raro"):
        print(f"{test!r:>18} ->", resolve_label(test))
