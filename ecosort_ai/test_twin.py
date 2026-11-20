"""test_twin.py - Pruebas del gemelo digital. Ejecutar con: pytest -v test_twin.py"""

import numpy as np
import pytest

from twin import layout
from twin.fusion import TactileReading, decide
from twin.kinematics import ArmGeometry, forward_kinematics, inverse_kinematics
from twin.sources import (CYCLE_S, DEMO_OBJECTS, DemoSource, build_read_packet, parse_response,
                          ticks_to_deg)


def test_ik_fk_roundtrip():
    geo = ArmGeometry()
    for target in [(140, 0, 15), (100, 80, 50), (-60, 120, 110), (120, -120, 30)]:
        q = inverse_kinematics(*target, geo=geo)
        assert q is not None, target
        tip = forward_kinematics(q, geo)["tip"]
        assert np.allclose(tip, target, atol=1e-6)


def test_ik_unreachable():
    assert inverse_kinematics(500, 0, 10) is None


def test_demo_timeline_always_reachable():
    demo = DemoSource()
    total = CYCLE_S * len(DEMO_OBJECTS)
    t = 0.0
    while t < total:
        assert demo.state_at(t).ok, f"fuera de alcance en t={t:.1f}"
        t += 0.1


def test_demo_decisions():
    demo = DemoSource()
    by_label = {o["label"]: demo.decision_for(i)[1] for i, o in enumerate(DEMO_OBJECTS)}
    assert by_label["botella de plástico"].bin == "reciclable"
    assert by_label["caja de cartón"].bin == "papel"
    assert by_label["cáscara de plátano"].bin == "organico"
    assert by_label["lata con etiqueta de papel"].action == "revisar"
    assert by_label["pila usada"].action == "revisar"
    state = demo.state_at(CYCLE_S * 4 + 3.0)
    assert state.tactile is not None and state.decision.action == "revisar"


def test_demo_tally():
    demo = DemoSource()
    assert sum(demo.tally(0.5).values()) == 0
    assert sum(demo.tally(CYCLE_S * 3 + 7.0).values()) == 4


def test_fusion_rules():
    plain = TactileReading(60, 15, False, 20)
    metal = TactileReading(60, 30, True, 15)
    assert decide("plastic", 0.9, plain).action == "depositar"
    assert decide("plastic", 0.4, plain).action == "revisar"
    assert decide("paper", 0.9, metal).action == "revisar"
    assert decide("metal", 0.9, plain).action == "revisar"
    assert decide("metal", 0.9, metal).bin == "reciclable"
    assert decide("none", 0.9).action == "ignorar"
    assert decide("electronic", 0.9, metal).action == "revisar"


def test_packet_build_and_parse():
    pkt = build_read_packet(3)
    assert pkt[:2] == b"\xff\xff" and pkt[2] == 3 and pkt[3] == 4
    body = [3, 4, 0, 0x00, 0x08]                 # id, len, error, pos bajo, pos alto (2048)
    resp = bytes([0xFF, 0xFF] + body + [(~sum(body)) & 0xFF])
    assert parse_response(resp, 3) == 2048
    assert parse_response(resp, 4) is None
    assert parse_response(resp[:-1] + b"\x00", 3) is None


def test_ticks_to_deg():
    assert ticks_to_deg(2048, 2048) == 0
    assert ticks_to_deg(3072, 2048) == pytest.approx(90.0)
    assert ticks_to_deg(3072, 2048, -1) == pytest.approx(-90.0)


def test_scene_builds():
    pytest.importorskip("plotly")
    from twin.scene import build_figure

    fig = build_figure(DemoSource().state_at(4.0))
    assert len(fig.data) > 10
