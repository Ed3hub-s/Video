"""Extract embedded raster images from a DOCX into assets/images/<chapter>/."""

from __future__ import annotations

import re
from pathlib import Path

from docx.document import Document as DocxDocument
from docx.parts.image import ImagePart


_SAFE_NAME = re.compile(r"[^a-z0-9._-]+", re.IGNORECASE)


def slugify(title: str) -> str:
    return _SAFE_NAME.sub("-", title.strip()).strip("-").lower() or "untitled"


def extract_images_from_paragraph(
    paragraph, chapter_dir: Path, image_counter: list[int]
) -> list[str]:
    """Return absolute paths of images found inside one paragraph's XML."""

    paths: list[str] = []
    p_element = paragraph._p
    blips = p_element.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
    for blip in blips:
        embed = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
        if not embed:
            continue
        part = paragraph.part.related_parts.get(embed)
        if part is None:
            continue
        image_counter[0] += 1
        ext = Path(part.partname or "image.png").suffix or ".png"
        target = chapter_dir / f"image-{image_counter[0]:03d}{ext}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(part.blob)
        paths.append(str(target))
    return paths


def detect_embedded_video(document: DocxDocument) -> bool:
    """Warn-level check: embedded video relationships are not supported in V1."""

    for rel in document.part.rels.values():
        if rel.reltype and "video" in rel.reltype:
            return True
    return False
