"""
gamification.py - Sistema de Eco-Puntos con persistencia en SQLite.

La clase EcoPointsManager administra usuarios, escaneos, ranking, insignias
y la detección de escaneos duplicados (misma imagen en una ventana de tiempo).
"""

import logging
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import BADGES, DB_PATH, DUPLICATE_WINDOW_HOURS

logger = logging.getLogger(__name__)


class EcoPointsManager:
    """Gestiona usuarios, puntos y escaneos en SQLite."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    @contextmanager
    def _connect(self):
        """Context manager: abre la conexión, hace commit/rollback y siempre la cierra."""
        conn = sqlite3.connect(self.db_path, timeout=30)  # timeout evita 'database is locked'
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Crea las tablas si no existen."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        total_points INTEGER NOT NULL DEFAULT 0
                    )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS scans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        class_name TEXT NOT NULL,
                        points INTEGER NOT NULL,
                        confidence REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        image_hash TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )"""
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id, timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_hash ON scans(image_hash)")
        except sqlite3.Error as exc:
            logger.error("Error inicializando la base de datos: %s", exc)
            raise

    def get_or_create_user(self, username):
        """Devuelve el id del usuario, creándolo si no existe."""
        username = str(username).strip()
        if not username:
            raise ValueError("El nombre de usuario no puede estar vacío")
        try:
            with self._connect() as conn:
                conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
                row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
                return int(row["id"])
        except sqlite3.Error as exc:
            logger.error("Error en get_or_create_user: %s", exc)
            raise

    def add_scan(self, user_id, class_name, points, confidence, image_hash):
        """Registra un escaneo y suma los puntos al usuario (en una sola transacción)."""
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO scans (user_id, class_name, points, confidence, timestamp, image_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, class_name, int(points), float(confidence), timestamp, image_hash),
                )
                conn.execute(
                    "UPDATE users SET total_points = total_points + ? WHERE id = ?",
                    (int(points), user_id),
                )
        except sqlite3.Error as exc:
            logger.error("Error en add_scan: %s", exc)
            raise

    def get_user_points(self, user_id):
        """Devuelve los puntos totales del usuario (0 si no existe)."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT total_points FROM users WHERE id = ?", (user_id,)).fetchone()
                return int(row["total_points"]) if row else 0
        except sqlite3.Error as exc:
            logger.error("Error en get_user_points: %s", exc)
            return 0

    def get_leaderboard(self, limit=10):
        """Devuelve los mejores usuarios: [{'rank', 'username', 'total_points', 'badge'}]."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT username, total_points FROM users ORDER BY total_points DESC, username ASC LIMIT ?",
                    (int(limit),),
                ).fetchall()
            return [
                {
                    "rank": i + 1,
                    "username": r["username"],
                    "total_points": int(r["total_points"]),
                    "badge": self._badge_for_points(int(r["total_points"])),
                }
                for i, r in enumerate(rows)
            ]
        except sqlite3.Error as exc:
            logger.error("Error en get_leaderboard: %s", exc)
            return []

    def is_duplicate_scan(self, image_hash, user_id, hours=DUPLICATE_WINDOW_HOURS):
        """True si el usuario ya registró esa imagen en las últimas `hours` horas."""
        if not image_hash:
            return False
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM scans WHERE image_hash = ? AND user_id = ? AND timestamp >= ? LIMIT 1",
                    (image_hash, user_id, cutoff),
                ).fetchone()
                return row is not None
        except sqlite3.Error as exc:
            logger.error("Error en is_duplicate_scan: %s", exc)
            return False

    def get_category_counts(self, user_id=None):
        """Cantidad de escaneos por categoría: {'plastic': 12, ...}. Sin user_id = toda la comunidad."""
        try:
            with self._connect() as conn:
                if user_id is None:
                    rows = conn.execute("SELECT class_name, COUNT(*) AS n FROM scans GROUP BY class_name").fetchall()
                else:
                    rows = conn.execute(
                        "SELECT class_name, COUNT(*) AS n FROM scans WHERE user_id = ? GROUP BY class_name",
                        (user_id,),
                    ).fetchall()
            return {r["class_name"]: int(r["n"]) for r in rows}
        except sqlite3.Error as exc:
            logger.error("Error en get_category_counts: %s", exc)
            return {}

    @staticmethod
    def _badge_for_points(points):
        """Devuelve la insignia más alta alcanzada con `points`."""
        current = "Sin insignia"
        for name, threshold in sorted(BADGES.items(), key=lambda kv: kv[1]):
            if points >= threshold:
                current = name
        return current

    def get_user_badge(self, user_id):
        """Devuelve la insignia actual del usuario."""
        return self._badge_for_points(self.get_user_points(user_id))

    def get_user_history(self, user_id, limit=5):
        """Últimos escaneos del usuario: [{'class_name','points','confidence','timestamp'}]."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT class_name, points, confidence, timestamp FROM scans "
                    "WHERE user_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                    (user_id, int(limit)),
                ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as exc:
            logger.error("Error en get_user_history: %s", exc)
            return []


if __name__ == "__main__":
    # Simulación de 3 escaneos con una base de datos temporal
    with tempfile.TemporaryDirectory() as tmp:
        manager = EcoPointsManager(Path(tmp) / "demo.db")
        ana = manager.get_or_create_user("ana")
        luis = manager.get_or_create_user("luis")

        manager.add_scan(ana, "plastic", 150, 0.91, "hash_a")
        manager.add_scan(ana, "metal", 200, 0.88, "hash_b")
        manager.add_scan(luis, "paper", 100, 0.75, "hash_c")

        print("¿Duplicado hash_a (ana)?:", manager.is_duplicate_scan("hash_a", ana))
        print("¿Duplicado hash_z (ana)?:", manager.is_duplicate_scan("hash_z", ana))
        print("Badge de ana:", manager.get_user_badge(ana))
        print("Historial de ana:", manager.get_user_history(ana))
        print("\n🏆 Leaderboard")
        for row in manager.get_leaderboard():
            print(f"{row['rank']}. {row['username']:<10} {row['total_points']:>5} pts  [{row['badge']}]")
