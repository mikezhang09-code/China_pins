#!/usr/bin/env python3
"""并发预热 Terrarium DEM 瓦片缓存，供 bake_relief.py 离线渲染。"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_relief import (  # noqa: E402
    GLOBAL_ZOOMS,
    REGIONAL_ZOOMS,
    REGIONAL_BOUNDS,
    WHOLE_IMAGE_MAX_PX,
    TILE_SIZE,
    fetch_tile,
    tile_range,
)


def jobs() -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for zoom in GLOBAL_ZOOMS:
        if 2 ** zoom * TILE_SIZE <= WHOLE_IMAGE_MAX_PX:
            continue  # z0-3 整图，已缓存或极少，交给 bake
        limit = 2 ** zoom
        for x in range(limit):
            for y in range(limit):
                out.append((zoom, x, y))
    for zoom in REGIONAL_ZOOMS:
        x0, x1, y0, y1 = tile_range(zoom, REGIONAL_BOUNDS)
        for x in range(x0, x1):
            for y in range(y0, y1):
                out.append((zoom, x, y))
    return out


def main() -> None:
    tiles = jobs()
    total = len(tiles)
    done = 0
    fails = 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = {pool.submit(fetch_tile, z, x, y): (z, x, y) for z, x, y in tiles}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                fails += 1
                if fails <= 10:
                    print(f"FAIL {futures[fut]}: {exc}", flush=True)
            done += 1
            if done % 100 == 0 or done == total:
                print(f"{done}/{total} cached ({fails} fails)", flush=True)
    print(f"Prefetch done: {total - fails}/{total} ok, {fails} fails", flush=True)


if __name__ == "__main__":
    main()
