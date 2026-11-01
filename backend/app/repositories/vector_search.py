"""Nearest-neighbour search on embedding columns.

On postgres, pgvector does it inside the database (<=> is cosine distance, sped up by
an HNSW index). SQLite (tests) has no vectors, so there we compare in Python with numpy.
"""
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session


def nearest(db: Session, model, vector: list[float], conditions: list, limit: int,
            column_name: str = "embedding") -> list[tuple[object, float]]:
    """rows of `model` closest to vector, as (row, similarity 0..1), best first"""
    column = getattr(model, column_name)
    conditions = [*conditions, column.is_not(None)]

    if db.get_bind().dialect.name == "postgresql":
        distance = column.cosine_distance(vector)
        rows = db.execute(select(model, distance).where(*conditions).order_by(distance).limit(limit))
        return [(row, 1 - float(d)) for row, d in rows]

    target = np.asarray(vector, dtype=float)
    scored = []
    for row in db.scalars(select(model).where(*conditions)):
        v = np.asarray(getattr(row, column_name), dtype=float)
        denom = np.linalg.norm(v) * np.linalg.norm(target)
        scored.append((row, float(v @ target / denom) if denom else 0.0))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
