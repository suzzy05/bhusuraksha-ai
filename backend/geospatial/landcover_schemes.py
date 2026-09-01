"""Real, published land-cover classification legends — used only to map a
raw raster class code to one of BHUSURAKSHA's normalized categories
(forest/grassland/cropland/urban/bare_land/water/unknown). A raster's
raw codes are meaningless without knowing which legend produced them, so
a scheme is only ever applied when explicitly configured
(BHUSURAKSHA_LANDCOVER_SCHEME) — never guessed from the file itself.
"""
from typing import Dict, Optional

# ESA WorldCover 10m v100/v200 (2020/2021), a real public global product —
# https://esa-worldcover.org. Codes per the product's own documented legend.
ESA_WORLDCOVER = {
    10: "forest",  # Tree cover
    20: "grassland",  # Shrubland (grouped with grassland — no distinct BHUSURAKSHA category)
    30: "grassland",  # Grassland
    40: "cropland",  # Cropland
    50: "urban",  # Built-up
    60: "bare_land",  # Bare / sparse vegetation
    70: "bare_land",  # Snow and ice (grouped with bare_land — no distinct category)
    80: "water",  # Permanent water bodies
    90: "water",  # Herbaceous wetland
    95: "forest",  # Mangroves
    100: "bare_land",  # Moss and lichen
}

SCHEMES: Dict[str, Dict[int, str]] = {
    "esa_worldcover": ESA_WORLDCOVER,
}

NORMALIZED_CATEGORIES = ("forest", "grassland", "cropland", "urban", "bare_land", "water", "unknown")


def normalize_class(scheme_name: Optional[str], raw_class) -> str:
    """Maps a raw class code to a normalized category using the named
    scheme. Returns "unknown" if no scheme is configured, the scheme name
    isn't recognized, or the raw code isn't in that scheme's legend —
    never guessed."""
    if not scheme_name:
        return "unknown"
    scheme = SCHEMES.get(scheme_name)
    if not scheme:
        return "unknown"
    try:
        return scheme.get(int(raw_class), "unknown")
    except (TypeError, ValueError):
        return "unknown"
