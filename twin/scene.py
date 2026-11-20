"""scene.py - Escena 3D (Plotly) del brazo, la mesa, la bandeja y los contenedores."""

import math

import plotly.graph_objects as go

from . import layout
from .fusion import BIN_NAMES
from .kinematics import ArmGeometry, forward_kinematics

BIN_COLORS = {"reciclable": "#2a9d8f", "papel": "#457b9d", "organico": "#8d6e3f", "revision": "#d62828"}


def _box_lines(cx, cy, size, height, z0=0.0):
    h = size / 2
    xs = [cx - h, cx + h, cx + h, cx - h, cx - h]
    ys = [cy - h, cy - h, cy + h, cy + h, cy - h]
    x, y, z = [], [], []
    for zz in (z0, z0 + height):
        x += xs + [None]; y += ys + [None]; z += [zz] * 5 + [None]
    for a, b in zip(xs[:4], ys[:4]):
        x += [a, a, None]; y += [b, b, None]; z += [z0, z0 + height, None]
    return x, y, z


def _line(points, name, color, width=8, markers=True):
    return go.Scatter3d(
        x=[p[0] for p in points], y=[p[1] for p in points], z=[p[2] for p in points],
        mode="lines+markers" if markers else "lines", name=name, hoverinfo="name",
        line=dict(color=color, width=width), marker=dict(size=5, color=color),
    )


def build_figure(state, geo=None, height=640):
    geo = geo or ArmGeometry()
    fk = forward_kinematics(state.q, geo)
    fig = go.Figure()

    # mesa
    s = 260
    fig.add_trace(go.Mesh3d(x=[-s, s, s, -s], y=[-s, -s, s, s], z=[0] * 4, i=[0, 0], j=[1, 2], k=[2, 3],
                            color="#e9e4d8", opacity=0.55, hoverinfo="skip", name="Mesa"))

    # bandeja y contenedores
    tx, ty = layout.polar_to_xy(*layout.TRAY)
    x, y, z = _box_lines(tx, ty, layout.TRAY_SIZE, 6)
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines", line=dict(color="#555", width=4),
                               hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter3d(x=[tx], y=[ty], z=[20], mode="text", text=["Bandeja de entrada"],
                               hoverinfo="skip", showlegend=False))
    for key, (r, th) in layout.BINS.items():
        bx, by = layout.polar_to_xy(r, th)
        x, y, z = _box_lines(bx, by, layout.BIN_SIZE, layout.BIN_HEIGHT)
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines", line=dict(color=BIN_COLORS[key], width=5),
                                   hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter3d(x=[bx], y=[by], z=[layout.BIN_HEIGHT + 14], mode="text",
                                   text=[BIN_NAMES[key]], textfont=dict(color=BIN_COLORS[key]),
                                   hoverinfo="skip", showlegend=False))

    # brazo
    chain = [fk["base"], fk["shoulder"], fk["elbow"], fk["wrist"], fk["tip"]]
    fig.add_trace(_line(chain, "Brazo", "#1d3557", width=10))
    fig.add_trace(_line([fk["finger_l"], fk["wrist"], fk["finger_r"]], "Pinza", "#e76f51", width=6))
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers", marker=dict(size=10, color="#1d3557"),
                               name="Base", hoverinfo="name"))

    # objeto
    if state.obj_xyz is not None:
        ox, oy, oz = state.obj_xyz
        fig.add_trace(go.Scatter3d(x=[ox], y=[oy], z=[oz], mode="markers",
                                   marker=dict(size=9, color="#f4a261", line=dict(color="#333", width=1)),
                                   name=state.obj_label or "Objeto", hoverinfo="name"))

    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, uirevision="twin",
        scene=dict(
            xaxis=dict(title="x (mm)", range=[-260, 260]), yaxis=dict(title="y (mm)", range=[-260, 260]),
            zaxis=dict(title="z (mm)", range=[0, 260]), aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.5), camera=dict(eye=dict(x=1.3, y=-1.5, z=0.9)),
        ),
    )
    return fig
