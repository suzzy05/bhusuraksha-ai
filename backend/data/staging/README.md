# Staging

Reserved for datasets in transit — e.g. a file downloaded by
`ingestion/connectors/nasa_landslide.py` before it has been validated and
moved into `data/raw/external/`. The download workflow itself currently
uses the OS temp directory for its intermediate `.part` file and moves
the result directly to the destination you specify (see
`docs/REAL_DATA_INGESTION.md`, "Safe download architecture"), so this
folder is currently empty by default — it exists as a designated,
gitignored location if a future connector needs an explicit
download-then-validate-then-promote staging step of its own.
