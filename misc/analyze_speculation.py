#!/usr/bin/env python3
"""
Analyze a speculation log produced by the compiler scheduler.

To generate a log, set the INMANTA_SPECULATION_LOG environment variable
before running a compile:

    INMANTA_SPECULATION_LOG=/tmp/speculation.json inmanta compile

Then analyze it:

    python misc/analyze_speculation.py /tmp/speculation.json

:copyright: 2026 Inmanta
:contact: code@inmanta.com
:license: Inmanta EULA
"""

import json
import sys
from collections import Counter
from pathlib import Path


def analyze(path: str) -> None:
    data = json.loads(Path(path).read_text())

    iterations = [d for d in data if d["type"] == "iteration"]
    freezes = [d for d in data if d["type"] == "freeze"]

    print(f"Speculation log: {path}")
    print(f"  Iterations: {len(iterations)}")
    print(f"  Speculative freezes: {len(freezes)}")
    print()

    # Progress source distribution
    sources = Counter(d["progress_source"] for d in iterations)
    print("Progress source distribution:")
    for src, cnt in sources.most_common():
        print(f"  {src:25s} {cnt:5d}")
    print()

    if not freezes:
        print("No speculative freezes — nothing to analyze.")
        return

    # Frozen entity.attribute distribution
    entity_attr = Counter()
    entity_only = Counter()
    for f in freezes:
        if "entity" in f and "attribute" in f:
            short_attr = f["attribute"].split(".")[-1]
            entity_attr[f["attribute"]] += 1
            entity_only[f["entity"]] += 1

    print(f"Frozen attributes ({len(entity_attr)} distinct):")
    for ea, cnt in entity_attr.most_common():
        print(f"  {cnt:5d}  {ea}")
    print()

    print(f"Frozen entity types ({len(entity_only)} distinct):")
    for e, cnt in entity_only.most_common():
        print(f"  {cnt:5d}  {e}")
    print()

    # Speculation phases (grouped by consecutive same attribute)
    phases = []
    current_phase = None
    phase_start = None
    phase_count = 0
    for f in freezes:
        attr = f.get("attribute", "?")
        if attr != current_phase:
            if current_phase is not None:
                phases.append((current_phase, phase_start, phase_count))
            current_phase = attr
            phase_start = f["iteration"]
            phase_count = 1
        else:
            phase_count += 1
    if current_phase:
        phases.append((current_phase, phase_start, phase_count))

    print(f"Speculation phases ({len(phases)} phases):")
    print(f"  {'#':>3s}  {'Start':>6s}  {'Count':>6s}  Attribute")
    print(f"  {'':->3s}  {'':->6s}  {'':->6s}  {'':->60s}")
    for idx, (attr, start, cnt) in enumerate(phases):
        print(f"  {idx+1:3d}  {start:6d}  {cnt:6d}  {attr}")
    print()

    # Queue evolution during speculation
    print("Queue evolution during speculation:")
    print(f"  {'Iter':>5s}  {'Waiters':>8s}  {'Cands':>6s}  {'Providers':>10s}  {'Potential':>10s}  Attribute")
    print(f"  {'':->5s}  {'':->8s}  {'':->6s}  {'':->10s}  {'':->10s}  {'':->50s}")
    for f in freezes[:40]:
        attr = f.get("attribute", "?")
        providers = f.get("waiting_providers", "?")
        potential = f.get("progress_potential", "?")
        print(f"  {f['iteration']:5d}  {f['allwaiters']:8d}  {f['candidates']:6d}  {providers:>10}  {potential:>10}  {attr}")
    if len(freezes) > 40:
        print(f"  ... ({len(freezes) - 40} more)")
    print()

    # Candidate attribute distribution across all freeze calls
    all_candidate_attrs: Counter = Counter()
    for f in freezes:
        if "candidate_attrs" in f:
            for attr, cnt in f["candidate_attrs"].items():
                all_candidate_attrs[attr] += cnt

    if all_candidate_attrs:
        print("Candidate attributes across all freeze calls:")
        for attr, cnt in all_candidate_attrs.most_common(15):
            print(f"  {cnt:6d}  {attr}")
        print()

    # Progress source by iteration range
    chunk_size = max(1, len(iterations) // 10)
    print(f"Progress source by iteration range (chunks of {chunk_size}):")
    for start in range(0, len(iterations), chunk_size):
        chunk = iterations[start : start + chunk_size]
        chunk_sources = Counter(d["progress_source"] for d in chunk)
        irange = f"{chunk[0]['iteration']:>4d}-{chunk[-1]['iteration']:>4d}"
        desc = ", ".join(f"{s}:{c}" for s, c in chunk_sources.most_common())
        print(f"  {irange}: {desc}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <speculation_log.json>")
        print()
        print("Generate a log by setting INMANTA_SPECULATION_LOG before compiling:")
        print("  INMANTA_SPECULATION_LOG=/tmp/speculation.json inmanta compile")
        sys.exit(1)
    analyze(sys.argv[1])
