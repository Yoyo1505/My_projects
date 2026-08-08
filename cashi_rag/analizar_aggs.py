#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import polars as pl
from pathlib import Path

aggs_dir = Path('aggs')
print("=== ESTRUCTURA DE AGGS (Cardinalidad y Dimensiones) ===\n")

results = []
for pq in sorted(aggs_dir.glob('*.parquet')):
    if pq.name.startswith('_'):
        continue
    try:
        df = pl.scan_parquet(str(pq)).collect()
        size_mb = pq.stat().st_size / 1e6
        results.append((pq.name, len(df), size_mb, len(df.columns)))
    except Exception as e:
        print(f"{pq.name:<30} ERROR: {e}")

# Imprimir ordenado
for name, rows, size_mb, cols in sorted(results, key=lambda x: -x[1]):
    print(f"{name:<30} {rows:>12,} rows | {size_mb:>7.1f} MB | {cols:>2} cols")

# Análisis de cardinalidad
print("\n=== ANÁLISIS DE CARDINALIDAD ===" )
total_rows = sum(r[1] for r in results)
total_size = sum(r[2] for r in results)
print(f"Total: {total_rows:,} filas | {total_size:.1f} MB")

# Aggs pesados (top 5)
print("\nTop 5 aggs por tamaño:")
for name, rows, size_mb, cols in sorted(results, key=lambda x: -x[2])[:5]:
    pct = (size_mb / total_size) * 100
    print(f"  {name:<30} {size_mb:>7.1f} MB ({pct:>5.1f}%)")
