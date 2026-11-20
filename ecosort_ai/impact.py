"""
impact.py - Impacto ambiental y ruta de economía circular de EcoSort AI.

Convierte los escaneos (conteo de residuos por categoría) en indicadores:
kg estimados, tasa de desviación del relleno sanitario y CO2e evitado, y
asocia cada categoría con su destino de valorización.

IMPORTANTE: los pesos y factores son ESTIMACIONES orientativas (ver SUPUESTOS).
Para reportar impacto real hay que pesar los residuos en el piloto y usar factores
de emisión locales. Los resultados de este módulo son una referencia, no una medición.
"""

from config import CLASS_NAMES_ES, POINTS_SYSTEM

# Peso promedio estimado por unidad registrada (kg). Calibrar pesando en el piloto.
AVG_WEIGHT_KG = {
    "plastic": 0.03,     # botella/envase PET pequeño
    "metal": 0.015,      # lata de aluminio
    "glass": 0.30,       # botella de vidrio
    "paper": 0.05,
    "organic": 0.15,
    "cardboard": 0.10,
    "trash": 0.05,
}

# kg de CO2e evitados por kg de material reciclado/valorizado en vez de ir a relleno.
# Valores orientativos de la literatura (p. ej. modelo WARM de la EPA de EE. UU.);
# deben sustituirse por factores locales y por el tipo exacto de material.
CO2E_AVOIDED_PER_KG = {
    "plastic": 1.0,
    "metal": 9.0,
    "glass": 0.3,
    "paper": 3.0,
    "organic": 0.2,
    "cardboard": 3.0,
    "trash": 0.0,
}

# Ruta de valorización por categoría. Los socios son TIPOS de actores a establecer
# (no hay convenios firmados): completar con nombres reales cuando existan.
CIRCULAR_ROUTES = {
    "plastic": {
        "destino": "Recicladora de plásticos (lavado, triturado y pellet)",
        "producto": "Plástico reciclado para nuevos envases o productos",
        "socio": "Gestor autorizado o recicladores de base",
    },
    "metal": {
        "destino": "Fundición / reciclaje de metales",
        "producto": "Aluminio y acero secundarios",
        "socio": "Gestor autorizado o recicladores de base",
    },
    "glass": {
        "destino": "Planta de reciclaje de vidrio",
        "producto": "Vidrio reciclado (calcín) para nuevos envases",
        "socio": "Gestor autorizado o punto de acopio de vidrio",
    },
    "paper": {
        "destino": "Papelera / planta de reciclaje de papel",
        "producto": "Pulpa y papel reciclado",
        "socio": "Gestor autorizado o recicladores de base",
    },
    "cardboard": {
        "destino": "Planta de reciclaje de cartón",
        "producto": "Cartón corrugado reciclado",
        "socio": "Gestor autorizado o recicladores de base",
    },
    "organic": {
        "destino": "Compostaje o valorización biológica",
        "producto": "Compost / enmienda para suelos",
        "socio": "Planta de compostaje o compostaje local",
    },
    "trash": {
        "destino": "Disposición final en relleno sanitario autorizado",
        "producto": "Sin aprovechamiento (objetivo: reducir este flujo)",
        "socio": "Servicio municipal de recolección",
    },
    "electronic": {
        "destino": "Gestión de residuos electrónicos (RAEE) con gestor autorizado",
        "producto": "Recuperación de metales y componentes",
        "socio": "Sistema de gestión / gestor autorizado de RAEE",
    },
}

SUPUESTOS = [
    "Los pesos son promedios por unidad (AVG_WEIGHT_KG), no mediciones reales.",
    "Los factores de CO2e son valores orientativos de la literatura; deben validarse con factores locales.",
    "Se asume que todo lo clasificado como reciclable llega efectivamente a valorización: "
    "eso depende de la contaminación y de la alianza con un gestor, y debe verificarse con trazabilidad.",
    "Solo cuenta lo registrado en la app; no mide lo que las personas no escanean.",
]


def compute_impact(counts):
    """Calcula indicadores a partir de {categoría: cantidad de unidades}.

    Returns:
        dict con: rows (detalle por categoría), items, kg_total, kg_valorizable,
        kg_trash, diversion_rate (0-1) y co2e_avoided (kg).
    """
    rows = []
    kg_total = kg_trash = co2e = 0.0
    items = 0
    for category in POINTS_SYSTEM:
        n = int(counts.get(category, 0))
        if n <= 0:
            continue
        kg = n * AVG_WEIGHT_KG.get(category, 0.0)
        co2 = kg * CO2E_AVOIDED_PER_KG.get(category, 0.0)
        items += n
        kg_total += kg
        co2e += co2
        if category == "trash":
            kg_trash += kg
        rows.append({
            "category": category,
            "categoria": CLASS_NAMES_ES.get(category, category),
            "unidades": n,
            "kg": round(kg, 3),
            "co2e_evitado_kg": round(co2, 3),
            "destino": CIRCULAR_ROUTES[category]["destino"],
        })
    kg_valorizable = kg_total - kg_trash
    return {
        "rows": rows,
        "items": items,
        "kg_total": round(kg_total, 3),
        "kg_valorizable": round(kg_valorizable, 3),
        "kg_trash": round(kg_trash, 3),
        "diversion_rate": (kg_valorizable / kg_total) if kg_total > 0 else 0.0,
        "co2e_avoided": round(co2e, 3),
    }


if __name__ == "__main__":
    demo = {"plastic": 40, "metal": 25, "glass": 6, "paper": 12, "organic": 10, "trash": 8}
    result = compute_impact(demo)
    print(f"Unidades: {result['items']} | kg: {result['kg_total']} | "
          f"desviación: {result['diversion_rate']:.0%} | CO2e evitado: {result['co2e_avoided']} kg")
    for r in result["rows"]:
        print(f"  {r['categoria']:<15} {r['unidades']:>3} u  {r['kg']:>6} kg  -> {r['destino']}")
