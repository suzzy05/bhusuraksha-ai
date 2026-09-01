"""Batched database inserts with clear transaction boundaries and
progress reporting — avoids holding an entire large dataset's ORM
objects in memory at once, and avoids one giant transaction where a
single bad record would roll back everything already safely stored.
"""
from typing import Callable, Iterable, List, Optional

DEFAULT_BATCH_SIZE = 500


def batched_insert(
    db,
    rows: Iterable,
    batch_size: int = DEFAULT_BATCH_SIZE,
    on_progress: Optional[Callable[[int], None]] = None,
) -> int:
    """`rows` yields already-constructed (but not yet session-added) ORM
    model instances. Commits every `batch_size` rows. Returns the total
    number of rows actually committed."""
    inserted = 0
    batch: List = []

    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            db.add_all(batch)
            db.commit()
            inserted += len(batch)
            if on_progress:
                on_progress(inserted)
            batch = []

    if batch:
        db.add_all(batch)
        db.commit()
        inserted += len(batch)
        if on_progress:
            on_progress(inserted)

    return inserted
