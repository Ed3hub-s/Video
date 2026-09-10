from __future__ import annotations

from pipeline.config import STYLES, load_config


def test_style_default_is_studio():
    assert load_config().style == "studio"


def test_all_style_names_available():
    assert {"studio", "dark", "playful", "minimal", "cinema"} <= set(STYLES)
