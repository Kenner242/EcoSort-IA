"""
prepare_dataset.py - Divide un dataset YOLO en train/val/test de forma reproducible.

Entrada (--source): carpeta con subcarpetas 'images/' y 'labels/' (formato YOLO,
un .txt por imagen con 'clase xc yc w h' normalizados).
Salida: dataset/images/{train,val,test} y dataset/labels/{train,val,test},
más un reporte de la distribución de clases (para detectar desbalance).

Uso:
    python scripts/prepare_dataset.py --source dataset/raw --seed 42
"""

import argparse
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ROOT = Path(__file__).resolve().parent.parent


def read_classes(label_path):
    """Devuelve el conjunto de clases presentes en un archivo de etiquetas."""
    classes = set()
    try:
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                classes.add(int(parts[0]))
    except (OSError, ValueError):
        pass
    return classes


def collect_pairs(source):
    """Empareja cada imagen con su etiqueta; ignora imágenes sin etiqueta."""
    images_dir, labels_dir = source / "images", source / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise FileNotFoundError(f"Se esperan las carpetas {images_dir} y {labels_dir}")
    pairs = []
    for img in sorted(images_dir.iterdir()):
        if img.suffix.lower() in IMAGE_EXTS:
            label = labels_dir / f"{img.stem}.txt"
            if label.is_file():
                pairs.append((img, label))
    return pairs


def split_pairs(pairs, train_ratio, val_ratio, seed):
    """Mezcla con semilla fija y reparte en train/val/test."""
    rng = random.Random(seed)
    shuffled = pairs[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train:n_train + n_val],
        "test": shuffled[n_train + n_val:],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Split reproducible de dataset YOLO")
    parser.add_argument("--source", default=str(ROOT / "dataset" / "raw"))
    parser.add_argument("--output", default=str(ROOT / "dataset"))
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--val", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if args.train + args.val >= 1.0:
        print("ERROR: train + val debe ser menor que 1.0 (el resto es test).")
        return 1
    try:
        pairs = collect_pairs(Path(args.source))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1
    if len(pairs) < 10:
        print(f"ERROR: solo {len(pairs)} pares imagen/etiqueta; se necesitan al menos 10.")
        return 1

    splits = split_pairs(pairs, args.train, args.val, args.seed)
    out = Path(args.output)
    for name, items in splits.items():
        img_dir, lbl_dir = out / "images" / name, out / "labels" / name
        for d in (img_dir, lbl_dir):
            if d.exists():
                shutil.rmtree(d)  # evita mezclar ejecuciones previas (data leakage)
            d.mkdir(parents=True)
        counts = Counter()
        for img, lbl in items:
            shutil.copy2(img, img_dir / img.name)
            shutil.copy2(lbl, lbl_dir / lbl.name)
            counts.update(read_classes(lbl))
        print(f"{name:<5}: {len(items):>5} imágenes | imágenes por clase: {dict(sorted(counts.items()))}")

    print(f"\nSplit completado (seed={args.seed}). Salida: {out}")
    print("Revisa que ninguna clase tenga muy pocas imágenes en val/test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
