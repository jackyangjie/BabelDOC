#!/usr/bin/env python3
"""Download BabelDOC model and font assets for offline Docker builds.

Usage:
    uv run python scripts/download_assets.py
    uv run python scripts/download_assets.py --upstream modelscope

Downloads assets to assets/cache/ with the same directory structure
as ~/.cache/babeldoc/, so they can be COPY'd directly into Docker.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import sys
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_ROOT = PROJECT_ROOT / "assets" / "cache"

# ---- Import metadata from the project ----
sys.path.insert(0, str(PROJECT_ROOT))
from babeldoc.assets.embedding_assets_metadata import (
    CMAP_METADATA,
    CMAP_URL_BY_UPSTREAM,
    DOC_LAYOUT_ONNX_MODEL_URL,
    DOCLAYOUT_YOLO_DOCSTRUCTBENCH_IMGSZ1024ONNX_SHA3_256,
    EMBEDDING_FONT_METADATA,
    FONT_URL_BY_UPSTREAM,
    TIKTOKEN_CACHES,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DEFAULT_UPSTREAM = "modelscope"


def verify_file(path: Path, sha3_256: str) -> bool:
    if not path.exists():
        return False
    h = hashlib.sha3_256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest() == sha3_256


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=15),
)
async def download(client: httpx.AsyncClient, url: str, path: Path):
    logger.info(f"  Downloading: {url}")
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


async def download_model(client: httpx.AsyncClient, upstream: str):
    """Download DocLayout YOLO ONNX model."""
    name = "doclayout_yolo_docstructbench_imgsz1024.onnx"
    dst = CACHE_ROOT / "models" / name
    sha3 = DOCLAYOUT_YOLO_DOCSTRUCTBENCH_IMGSZ1024ONNX_SHA3_256

    if verify_file(dst, sha3):
        logger.info(f"  [OK] {name}")
        return

    url = DOC_LAYOUT_ONNX_MODEL_URL[upstream]
    await download(client, url, dst)
    if not verify_file(dst, sha3):
        dst.unlink(missing_ok=True)
        raise ValueError(f"Corrupted: {name}")
    logger.info(f"  [OK] {name}")


async def download_fonts(client: httpx.AsyncClient, upstream: str):
    """Download all embedded fonts."""
    total = len(EMBEDDING_FONT_METADATA)
    for i, (name, meta) in enumerate(EMBEDDING_FONT_METADATA.items(), 1):
        dst = CACHE_ROOT / "fonts" / name
        sha3 = meta["sha3_256"]

        if verify_file(dst, sha3):
            logger.info(f"  [{i}/{total}] [OK] {name}")
            continue

        url = FONT_URL_BY_UPSTREAM[upstream](name)
        await download(client, url, dst)
        if not verify_file(dst, sha3):
            dst.unlink(missing_ok=True)
            raise ValueError(f"Corrupted: {name}")
        logger.info(f"  [{i}/{total}] [OK] {name}")


async def download_cmap(client: httpx.AsyncClient, upstream: str):
    """Download CMAP files."""
    total = len(CMAP_METADATA)
    for i, (name, meta) in enumerate(CMAP_METADATA.items(), 1):
        dst = CACHE_ROOT / "cmap" / name
        sha3 = meta["sha3_256"]

        if verify_file(dst, sha3):
            logger.info(f"  [{i}/{total}] [OK] {name}")
            continue

        url = CMAP_URL_BY_UPSTREAM[upstream](name)
        await download(client, url, dst)
        if not verify_file(dst, sha3):
            dst.unlink(missing_ok=True)
            raise ValueError(f"Corrupted: {name}")
        logger.info(f"  [{i}/{total}] [OK] {name}")


async def main():
    parser = argparse.ArgumentParser(description="Download BabelDOC assets")
    parser.add_argument(
        "--upstream",
        default=DEFAULT_UPSTREAM,
        choices=["modelscope", "huggingface", "hf-mirror"],
        help="Download source",
    )
    args = parser.parse_args()

    logger.info(f"Cache root: {CACHE_ROOT}")
    logger.info(f"Upstream:   {args.upstream}")
    logger.info("")

    timeout = httpx.Timeout(120.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # 1. ONNX model (~33 MB)
        logger.info("=== DocLayout ONNX Model ===")
        await download_model(client, args.upstream)
        logger.info("")

        # 2. CMAP files
        logger.info(f"=== CMAP Files ({len(CMAP_METADATA)}) ===")
        await download_cmap(client, args.upstream)
        logger.info("")

        # 3. Fonts
        logger.info(f"=== Fonts ({len(EMBEDDING_FONT_METADATA)}) ===")
        await download_fonts(client, args.upstream)
        logger.info("")

    logger.info("=== Done ===")
    logger.info(f"Total size: check with: du -sh {CACHE_ROOT}")


if __name__ == "__main__":
    asyncio.run(main())
