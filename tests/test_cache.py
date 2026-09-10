from __future__ import annotations

from pipeline.cache.cache import FileCache, hash_json, hash_text


def test_hash_is_stable():
    assert hash_text("hello") == hash_text("hello")
    assert hash_json({"a": 1, "b": [1, 2]}) == hash_json({"b": [1, 2], "a": 1})


def test_cache_roundtrip(tmp_path):
    cache = FileCache(tmp_path / "cache")
    assert cache.get("key-1") is None
    cache.put("key-1", {"scenes": [1, 2, 3]})
    assert cache.get("key-1") == {"scenes": [1, 2, 3]}


def test_cache_misses_unknown_key(tmp_path):
    cache = FileCache(tmp_path / "cache")
    assert cache.get("never-written") is None
