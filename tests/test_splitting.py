from __future__ import annotations

from pipeline.config import load_config
from pipeline.content.schemas import SourceBlock, SourceBlockType
from pipeline.content.text_splitter import split_paragraph_into_chunks, split_source_block, word_count


def test_short_text_not_split():
    text = "Short paragraph stays whole."
    assert split_paragraph_into_chunks(text, load_config()) == [text]


def test_long_paragraph_split_at_sentence_boundaries():
    config = load_config()
    sentence = "This is one complete sentence with enough words in it to count."
    text = " ".join([sentence] * 30)
    chunks = split_paragraph_into_chunks(text, config)
    assert len(chunks) > 1
    assert all(word_count(c) <= config.max_narration_words for c in chunks)


def test_bullets_split_to_max_five():
    config = load_config()
    block = SourceBlock(type=SourceBlockType.BULLETS, items=[f"item {i}" for i in range(12)])
    chunks = split_source_block(block, config)
    assert all(len(c.items) <= config.max_bullets for c in chunks)
    assert sum(len(c.items) for c in chunks) == 12


def test_image_block_passthrough():
    config = load_config()
    block = SourceBlock(type=SourceBlockType.IMAGE, path="assets/images/x.png")
    assert split_source_block(block, config) == [block]
