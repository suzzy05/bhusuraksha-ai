# Training data — DEMO / SYNTHETIC

`landslide_training_data.csv` is **synthetic, hand-crafted demo data**, not a
real-world landslide dataset. It was generated deterministically (fixed
random seed `42`) by [`../../generate_dataset.py`](../../generate_dataset.py)
to exercise the Phase 2 ML pipeline end-to-end.

Do not treat model metrics trained on this file as reflecting real-world
predictive accuracy. Everything under `data/raw/demo/` is synthetic by
definition — real, externally-sourced datasets belong in
[`../external/`](../external/) instead, and are never mixed into this
folder. See [`../../README.md`](../../README.md) for how the two are kept
separate.
