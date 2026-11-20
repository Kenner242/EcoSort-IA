"""
digital_twin.py - Gemelo digital del brazo robótico de EcoSort AI.

Ejecutar con:  streamlit run digital_twin.py

Fuentes de datos:
  - Demostración: simula el ciclo completo (visión + tacto + decisión). No necesita robot.
  - Sliders manuales: mueves cada articulación y ves el brazo.
  - Robot por USB: lee las posiciones de los servos (solo lectura, ver twin/sources.py).
"""

import time

import streamlit as st

from twin.fusion import BIN_NAMES
from twin.kinematics import ArmGeometry
from twin.scene import build_figure
from twin.sources import CYCLE_S, DEMO_OBJECTS, DemoSource, ManualSource, SerialSource, load_calibration

st.set_page_config(layout="wide", page_title="Gemelo digital EcoSort", page_icon="🦾")
st.title("🦾 Gemelo digital del brazo EcoSort")

geo = ArmGeometry()
demo = DemoSource(geo)

st.sidebar.header("Fuente de datos")
source = st.sidebar.radio("Origen del movimiento", ["Demostración", "Sliders manuales", "Robot por USB"])
FPS_PAUSE = 0.12

CATEGORIES_ES = {"plastic": "plástico", "metal": "metal", "glass": "vidrio", "paper": "papel",
                 "cardboard": "cartón", "organic": "orgánico", "trash": "no aprovechable",
                 "electronic": "electrónico"}

chart_col, panel_col = st.columns([3, 2])
chart_ph = chart_col.empty()
panel_ph = panel_col.empty()


def render(state, tally=None):
    chart_ph.plotly_chart(build_figure(state, geo), use_container_width=True)
    with panel_ph.container():
        st.subheader(state.phase or "En espera")
        if not state.ok:
            st.error(state.message)
        if state.obj_label:
            st.markdown(f"**Objeto:** {state.obj_label}")
            st.markdown(f"**Cámara:** {CATEGORIES_ES.get(state.vision_category, state.vision_category)} "
                        f"({state.vision_conf:.0%})")
        if state.tactile is not None:
            t = state.tactile
            st.markdown("**Sensores táctiles**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tamaño", f"{t.size_mm:.0f} mm")
            c2.metric("Corriente", f"{t.current_ma:.0f} mA")
            c3.metric("Metal", "Sí" if t.is_metal else "No")
            c4.metric("Peso", f"{t.weight_g:.0f} g")
        if state.decision is not None:
            d = state.decision
            msg = f"**{d.action.capitalize()}** → {BIN_NAMES[d.bin]}. {d.reason}"
            (st.success if d.action == "depositar" else st.warning)(msg)
        q = state.q
        st.caption(f"Ángulos: base {q[0]:.0f}°, hombro {q[1]:.0f}°, codo {q[2]:.0f}°, "
                   f"muñeca {q[3]:.0f}°, pinza {q[4]:.0f} mm")
        if tally is not None:
            st.markdown("**Contenedores**")
            cols = st.columns(len(BIN_NAMES))
            for col, (key, name) in zip(cols, BIN_NAMES.items()):
                col.metric(name, tally[key])


if source == "Demostración":
    speed = st.sidebar.slider("Velocidad", 0.25, 3.0, 1.0, 0.25)
    live = st.sidebar.toggle("En vivo", value=True)
    st.sidebar.caption(f"Ciclo de {CYCLE_S} s por objeto; {len(DEMO_OBJECTS)} objetos de ejemplo. "
                       "La lata con etiqueta de papel es una trampa: la cámara se equivoca y el tacto lo detecta.")
    if live:
        t0 = time.time() - st.session_state.get("t_live", 0.0) / speed
        while True:
            t = (time.time() - t0) * speed
            st.session_state["t_live"] = t
            render(demo.state_at(t), demo.tally(t))
            time.sleep(FPS_PAUSE)
    else:
        t = st.sidebar.slider("Tiempo (s)", 0.0, CYCLE_S * len(DEMO_OBJECTS), 0.0, 0.1)
        render(demo.state_at(t), demo.tally(t))

elif source == "Sliders manuales":
    lims = geo.limits
    q = [
        st.sidebar.slider("Base (°)", *map(float, lims[0]), 0.0),
        st.sidebar.slider("Hombro (°)", *map(float, lims[1]), 45.0),
        st.sidebar.slider("Codo (°)", *map(float, lims[2]), -90.0),
        st.sidebar.slider("Muñeca (°)", *map(float, lims[3]), -45.0),
        st.sidebar.slider("Pinza (mm)", *map(float, lims[4]), 40.0),
    ]
    render(ManualSource().state(q))

else:
    port = st.sidebar.text_input("Puerto serie", value="COM3", help="En Windows: Administrador de dispositivos → Puertos")
    cal_path = st.sidebar.text_input("Archivo de calibración", value="twin_calibration.json")
    connect = st.sidebar.toggle("Conectar y leer")
    st.sidebar.warning("Solo lectura. Verifica el registro y la calibración con la hoja de datos de tus servos.")
    if not connect:
        st.info("Conecta el robot por USB, ajusta twin_calibration.json y activa 'Conectar y leer'.")
    else:
        try:
            robot = SerialSource(port, load_calibration(cal_path))
        except Exception as exc:
            st.error(f"No se pudo abrir el robot: {exc}")
        else:
            try:
                while True:
                    render(robot.state())
                    time.sleep(FPS_PAUSE)
            finally:
                robot.close()
