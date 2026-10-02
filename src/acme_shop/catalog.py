"""Seed catalog: fictional products for the demo store."""

from __future__ import annotations

from typing import NamedTuple


class SeedProduct(NamedTuple):
    sku: str
    name: str
    description: str
    price_cents: int


CATALOG: tuple[SeedProduct, ...] = (
    SeedProduct("ACME-ANV-001", "Anvil", "Classic 50 kg drop-forged anvil.", 12999),
    SeedProduct("ACME-RKT-002", "Rocket Skates", "Strap-on skates, one speed: fast.", 8950),
    SeedProduct("ACME-MAG-003", "Giant Magnet", "Horseshoe magnet for very large jobs.", 4500),
    SeedProduct("ACME-SPR-004", "Spring Shoes", "Coil-loaded footwear for tall jumps.", 3999),
    SeedProduct("ACME-BRD-005", "Bird Seed", "Premium seed, 5 kg bag.", 799),
    SeedProduct("ACME-UMB-006", "Umbrella", "Reinforced umbrella, falling-object rated.", 2450),
    SeedProduct("ACME-TNT-007", "Fireworks Kit", "Celebration kit with a long fuse.", 1999),
    SeedProduct("ACME-HOL-008", "Portable Hole", "Fold-out hole, fits in a pocket.", 15000),
)
