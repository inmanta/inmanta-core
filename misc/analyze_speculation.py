"""
Copyright 2026 Inmanta

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact: code@inmanta.com
"""

import json
import sys
from collections import Counter
from pathlib import Path


def frozen_attribute(freeze: dict) -> str:
    """Return the frozen relation attribute name, falling back to the variable type for non-relation variables."""
    return freeze["relation"]["attribute"] if freeze["relation"] is not None else freeze["var_type"]


def analyze(path: str) -> None:
    iterations = json.loads(Path(path).read_text())

    # Flatten the freeze records, keeping the iteration number of the enclosing iteration record
    freezes = [{**it["freeze"], "iteration": it["iteration"]} for it in iterations if it["freeze"] is not None]

    print(f"Speculation log: {path}")
    print(f"  Iterations: {len(iterations)}")
    print(f"  Speculative freezes: {len(freezes)}")
    print()

    # Progress source distribution
    sources = Counter(it["progress_source"] for it in iterations)
    print("Progress source distribution:")
    for src, cnt in sources.most_common():
        print(f"  {src:25s} {cnt:5d}")
    print()

    if not freezes:
        print("No speculative freezes — nothing to analyze.")
        return

    # Frozen entity.attribute distribution
    entity_attr: Counter[str] = Counter()
    entity_only: Counter[str] = Counter()
    for f in freezes:
        relation = f["relation"]
        if relation is not None:
            entity_attr[relation["attribute"]] += 1
            entity_only[relation["entity"]] += 1

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
        attr = frozen_attribute(f)
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
        print(f"  {idx + 1:3d}  {start:6d}  {cnt:6d}  {attr}")
    print()

    # Queue evolution during speculation
    print("Queue evolution during speculation:")
    print(f"  {'Iter':>5s}  {'Waiters':>8s}  {'Cands':>6s}  {'Providers':>10s}  {'Potential':>10s}  Attribute")
    print(f"  {'':->5s}  {'':->8s}  {'':->6s}  {'':->10s}  {'':->10s}  {'':->50s}")
    for f in freezes[:40]:
        print(
            f"  {f['iteration']:5d}  {f['allwaiters']:8d}  {f['candidates']:6d}"
            f"  {f['waiting_providers']:10d}  {f['progress_potential']:10d}  {frozen_attribute(f)}"
        )
    if len(freezes) > 40:
        print(f"  ... ({len(freezes) - 40} more)")
    print()

    # Candidate attribute distribution across all freeze calls
    all_candidate_attrs: Counter[str] = Counter()
    for f in freezes:
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
        chunk_sources = Counter(it["progress_source"] for it in chunk)
        irange = f"{chunk[0]['iteration']:>4d}-{chunk[-1]['iteration']:>4d}"
        desc = ", ".join(f"{s}:{c}" for s, c in chunk_sources.most_common())
        print(f"  {irange}: {desc}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <speculation_log.json>")
        print()
        print("Generate a log by setting the compiler.speculation_log_file option before compiling:")
        print("  INMANTA_COMPILER_SPECULATION_LOG_FILE=/tmp/speculation.json inmanta compile")
        sys.exit(1)
    analyze(sys.argv[1])
