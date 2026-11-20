"""
evaluate.py - Evalúa el modelo en el conjunto de TEST (nunca visto en el entrenamiento).

Imprime y guarda en reports/ métricas globales y por clase (precision, recall, AP50)
para detectar clases débiles. Las matrices de confusión las genera ultralytics en runs/.

Uso:
    python scripts/evaluate.py --data data.yaml --model models/best.pt
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluación en test - EcoSort AI")
    parser.add_argument("--data", default=str(ROOT / "data.yaml"))
    parser.add_argument("--model", default=str(ROOT / "models" / "best.pt"))
    parser.add_argument("--split", default="test", choices=["val", "test"])
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)

    if not Path(args.model).exists():
        print(f"ERROR: no existe el modelo {args.model}. Entrena primero con train.py.")
        return 1
    if not Path(args.data).exists():
        print(f"ERROR: no existe {args.data}.")
        return 1

    try:
        from ultralytics import YOLO
        model = YOLO(args.model)
        metrics = model.val(data=args.data, split=args.split, imgsz=args.imgsz,
                            device=args.device, project=str(ROOT / "runs"), name="eval", exist_ok=True)
    except Exception as exc:
        print(f"ERROR durante la evaluación: {exc}")
        return 1

    names = metrics.names
    rows = []
    for i, cls_idx in enumerate(metrics.box.ap_class_index):
        rows.append({
            "class": names[int(cls_idx)],
            "precision": round(float(metrics.box.p[i]), 4),
            "recall": round(float(metrics.box.r[i]), 4),
            "AP50": round(float(metrics.box.ap50[i]), 4),
            "AP50-95": round(float(metrics.box.ap[i]), 4),
        })
    summary = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "split": args.split,
        "mAP50": round(float(metrics.box.map50), 4),
        "mAP50-95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
        "per_class": rows,
    }

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "eval_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(reports / "eval_per_class.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "precision", "recall", "AP50", "AP50-95"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== Resultados en {args.split} ===")
    print(f"mAP50 {summary['mAP50']} | mAP50-95 {summary['mAP50-95']} | "
          f"P {summary['precision']} | R {summary['recall']}")
    for r in rows:
        print(f"  {r['class']:<10} P={r['precision']:.3f} R={r['recall']:.3f} AP50={r['AP50']:.3f}")
    print(f"\nGuardado en {reports}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
