"""
app.py - Dashboard Streamlit de EcoSort AI (interfaz en español).

Permite capturar o subir una imagen, identificar objetos y residuos,
otorgar Eco-Puntos (evitando duplicados con phash) y ver el ranking.

Ejecutar con:  streamlit run app.py

ADVERTENCIA sobre la cámara:
 - En LOCAL (localhost) st.camera_input funciona directamente en el navegador.
 - En CLOUD (Streamlit Cloud, servidores remotos) el navegador SOLO permite la
   cámara si la página se sirve por HTTPS; la cámara es la del cliente, no la del
   servidor. Para usar una cámara conectada al servidor (p. ej. Raspberry Pi)
   utiliza raspi_controller.py, no esta app.

Si ves el error "removeChild" en pantalla, desactiva el traductor automático del
navegador para localhost: no es un fallo del programa.
"""

import cv2
import imagehash
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

from config import BADGES, DB_PATH, MODEL_PATH, POINTS_SYSTEM, display_name
from detector import WasteDetector
from gamification import EcoPointsManager
from impact import CIRCULAR_ROUTES, SUPUESTOS, compute_impact

st.set_page_config(layout="wide", page_title="EcoSort AI", page_icon="♻️")


# ---------------------------------------------------------------
# Recursos compartidos (se cargan una sola vez por servidor)
# ---------------------------------------------------------------
@st.cache_resource(show_spinner="Cargando modelo de detección (la primera vez descarga archivos)...")
def load_detector():
    """Carga el detector una sola vez (evita recargar el modelo en cada interacción)."""
    return WasteDetector(str(MODEL_PATH))


@st.cache_resource
def load_manager():
    """Crea el gestor de puntos (cada operación abre su propia conexión SQLite)."""
    return EcoPointsManager(DB_PATH)


detector = load_detector()
manager = load_manager()

if detector.model is None:
    st.error("⚠️ No se pudo cargar ningún modelo. Revisa la instalación de ultralytics y tu conexión a internet.")

# ---------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("username", "")
st.session_state.setdefault("analysis_cache", {})  # evita recalcular la misma imagen

# ---------------------------------------------------------------
# Sidebar: usuario (las métricas se pintan al final para reflejar cambios)
# ---------------------------------------------------------------
st.sidebar.title("♻️ EcoSort AI")
username_input = st.sidebar.text_input("Nombre de usuario", max_chars=32, placeholder="Ej: ana")
stats_box = st.sidebar.container()

username = username_input.strip()
if username and username != st.session_state["username"]:
    try:
        st.session_state["user_id"] = manager.get_or_create_user(username)
        st.session_state["username"] = username
    except Exception as exc:
        st.sidebar.error(f"No se pudo iniciar sesión: {exc}")
elif not username:
    st.session_state["user_id"] = None
    st.session_state["username"] = ""

user_id = st.session_state["user_id"]


# ---------------------------------------------------------------
# Lógica de análisis
# ---------------------------------------------------------------
def analyze_image(pil_img):
    """Detecta objetos, calcula hash y puntos. Resultado cacheado por hash de imagen."""
    image_hash = str(imagehash.phash(pil_img))
    cache = st.session_state["analysis_cache"]
    if image_hash in cache:
        return cache[image_hash]

    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    annotated_bgr, detections = detector.detect_from_frame(bgr)
    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)

    # El "residuo principal" es la detección de residuo con más confianza
    wastes = [d for d in detections if d["is_waste"]]
    best = max(wastes, key=lambda d: d["confidence"]) if wastes else None
    points = (
        detector.get_points_for_detection(best["class_name"], best["confidence"], detector.points_threshold)
        if best else 0
    )

    analysis = {
        "hash": image_hash,
        "annotated": annotated_rgb,
        "detections": detections,
        "best": best,
        "points": points,
    }
    if len(cache) > 20:  # límite simple de memoria
        cache.clear()
    cache[image_hash] = analysis
    return analysis


def render_scan_panel(pil_img, key_prefix):
    """Muestra detección + botón 'Confirmar y sumar puntos'."""
    try:
        analysis = analyze_image(pil_img)
    except Exception as exc:
        st.error(f"Error analizando la imagen: {exc}")
        return

    col_a, col_b = st.columns(2)
    col_a.image(pil_img, caption="Imagen original", use_container_width=True)
    col_b.image(analysis["annotated"], caption="Detección", use_container_width=True)

    detections = analysis["detections"]
    if not detections:
        st.info("No se detectó ningún objeto. Acércalo a la cámara, mejora la luz o prueba otro ángulo.")
        return

    table = pd.DataFrame([
        {
            "Objeto": d["label_es"],
            "Categoría": d["category_es"],
            "¿Es residuo?": "Sí" if d["is_waste"] else "No",
            "Confianza": f"{d['confidence']:.0%}",
        }
        for d in detections
    ])
    st.dataframe(table, use_container_width=True, hide_index=True)

    best, points = analysis["best"], analysis["points"]
    if best is None:
        seen = ", ".join(sorted({d["label_es"] for d in detections}))
        st.info(f"Se ve: {seen}. No hay ningún residuo clasificable en la imagen, por eso no hay puntos.")
    elif points > 0:
        st.success(
            f"Residuo principal: **{best['label_es']}** → categoría **{best['category_es']}** "
            f"({best['confidence']:.0%}) → **{points} Eco-Puntos**"
        )
    else:
        st.warning(
            f"**{best['label_es']}** ({best['confidence']:.0%}): la confianza está por debajo del "
            f"mínimo para dar puntos ({detector.points_threshold:.0%}). Prueba con una foto más nítida."
        )

    disabled = user_id is None or points == 0
    if user_id is None:
        st.caption("👈 Ingresa tu nombre de usuario en la barra lateral para sumar puntos.")

    if st.button("Confirmar y sumar puntos", key=f"{key_prefix}_confirm", disabled=disabled, type="primary"):
        try:
            if manager.is_duplicate_scan(analysis["hash"], user_id):
                st.warning("🔁 Esta imagen ya fue registrada recientemente. No se suman puntos duplicados.")
            else:
                manager.add_scan(user_id, best["class_name"], points, best["confidence"], analysis["hash"])
                st.success(f"✅ ¡+{points} Eco-Puntos!")
                st.balloons()
        except Exception as exc:
            st.error(f"No se pudo guardar el escaneo: {exc}")


# ---------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------
st.caption(f"Modo de detección: **{detector.mode_description}**")
tab_cam, tab_upload, tab_board, tab_impact = st.tabs(
    ["📷 Cámara en Vivo", "🖼️ Subir Imagen", "🏆 Clasificación", "🌍 Impacto ambiental"]
)

with tab_cam:
    st.caption("Usa la cámara de tu navegador (en cloud requiere HTTPS).")
    photo = st.camera_input("Toma una foto del residuo")
    if photo is not None:
        try:
            render_scan_panel(Image.open(photo).convert("RGB"), "cam")
        except Exception as exc:
            st.error(f"No se pudo leer la foto: {exc}")

with tab_upload:
    uploaded = st.file_uploader("Sube una imagen del residuo", type=["jpg", "jpeg", "png", "webp"])
    if uploaded is not None:
        try:
            render_scan_panel(Image.open(uploaded).convert("RGB"), "upload")
        except Exception as exc:
            st.error(f"Imagen inválida: {exc}")

with tab_board:
    board = manager.get_leaderboard(limit=10)
    if board:
        board_df = pd.DataFrame(board).rename(columns={
            "rank": "Puesto", "username": "Usuario", "total_points": "Eco-Puntos", "badge": "Insignia",
        })
        left, right = st.columns([1, 1])
        left.dataframe(board_df, use_container_width=True, hide_index=True)
        fig = px.bar(board_df, x="Usuario", y="Eco-Puntos", color="Insignia", title="Top Eco-Recicladores")
        right.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aún no hay usuarios con puntos. ¡Sé el primero!")

    with st.expander("Tabla de puntos y niveles"):
        st.write(pd.DataFrame([(display_name(k), v) for k, v in POINTS_SYSTEM.items()],
                              columns=["Residuo", "Puntos"]))
        st.write(pd.DataFrame(list(BADGES.items()), columns=["Insignia", "Puntos mínimos"]))


with tab_impact:
    st.subheader("Impacto ambiental y economía circular")
    options = ["Toda la comunidad"] + (["Solo mis residuos"] if user_id is not None else [])
    scope = st.radio("Ver datos de:", options, horizontal=True)
    counts = manager.get_category_counts(user_id if scope == "Solo mis residuos" else None)
    impact = compute_impact(counts)

    if impact["items"] == 0:
        st.info("Aún no hay residuos registrados. Confirma escaneos para ver el impacto.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Residuos registrados", impact["items"])
        m2.metric("Peso estimado", f"{impact['kg_total']:.2f} kg")
        m3.metric("Desviado de relleno", f"{impact['diversion_rate']:.0%}")
        m4.metric("CO₂e evitado (est.)", f"{impact['co2e_avoided']:.2f} kg")

        impact_df = pd.DataFrame(impact["rows"])
        fig_kg = px.bar(impact_df, x="categoria", y="kg", title="Peso estimado por tipo de residuo",
                        labels={"categoria": "Categoría", "kg": "kg"})
        st.plotly_chart(fig_kg, use_container_width=True)

        st.markdown("**¿A dónde va cada material? (ruta de economía circular)**")
        routes_df = pd.DataFrame([
            {"Residuo": r["categoria"], "Unidades": r["unidades"], "Destino": r["destino"],
             "Producto": CIRCULAR_ROUTES[r["category"]]["producto"],
             "Socio requerido": CIRCULAR_ROUTES[r["category"]]["socio"]}
            for r in impact["rows"]
        ])
        st.dataframe(routes_df, use_container_width=True, hide_index=True)

    with st.expander("Supuestos y límites (léelo antes de citar estas cifras)"):
        for item in SUPUESTOS:
            st.write(f"• {item}")

# ---------------------------------------------------------------
# Sidebar (al final para reflejar los puntos recién sumados)
# ---------------------------------------------------------------
with stats_box:
    if user_id is not None:
        st.metric("Eco-Puntos", manager.get_user_points(user_id))
        st.write(f"🏅 Insignia: **{manager.get_user_badge(user_id)}**")
        st.subheader("Últimos 5 escaneos")
        history = manager.get_user_history(user_id, limit=5)
        if history:
            for h in history:
                st.write(f"• {display_name(h['class_name'])} — {h['points']} pts ({h['confidence']:.0%})")
        else:
            st.caption("Sin escaneos todavía.")
    else:
        st.info("Ingresa un usuario para comenzar.")


if __name__ == "__main__":
    # Esta app se lanza con Streamlit; ejecutar con python no inicia el servidor.
    print("Ejecuta con: streamlit run app.py")
