#!/usr/bin/env python3
"""
sync-relaxation.py — Generate/update .harness/exploration/.gate-relaxation.yaml
from the manifest.

This file is the contract that other gates read to know which paths are
exempt from their checks. It is regenerated on every spike create/close to
reflect the current set of active spike sandboxes.

Consumer contract (for future gate updates):
    Gates that want to honor exploration's relaxation should read
    .harness/exploration/.gate-relaxation.yaml and skip files matching
    any pattern under their target.

Schema of .gate-relaxation.yaml:
    schema_version: 1
    generated_at: <ISO-8601>
    relaxations:
      - target: "boundaries"
        paths: [".harness/exploration/spikes/<spike-id>/sandbox/**", ...]
        reason: "..."
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required.", file=sys.stderr)
    sys.exit(2)


MANIFEST = Path(__file__).resolve().parent.parent / "manifest.yaml"
SPIKES_DIR = Path(".harness/exploration/spikes")
RELAX_FILE = Path(".harness/exploration/.gate-relaxation.yaml")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def expand_paths(pattern: str, spike_ids: list[str]) -> list[str]:
    """Expand <spike-id> placeholder against active spikes.

    Glob wildcards (* and **) in the pattern are preserved verbatim — they're
    interpreted by the gate consumer, not by this script.
    """
    if "<spike-id>" not in pattern:
        return [pattern]
    return [pattern.replace("<spike-id>", sid) for sid in spike_ids]


def active_spike_ids() -> list[str]:
    """Return spike IDs in 'questioning' or 'spiking' state."""
    if not SPIKES_DIR.exists():
        return []
    out = []
    for d in sorted(SPIKES_DIR.iterdir()):
        if not d.is_dir():
            continue
        f = d / "spike.yaml"
        if not f.exists():
            continue
        with f.open() as fh:
            data = yaml.safe_load(fh) or {}
        if data.get("status") in ("questioning", "spiking"):
            out.append(data.get("id", d.name))
    return out


def main():
    if not MANIFEST.exists():
        # Could be running in a project where exploration is installed under
        # .harness/methodologies. Try that path.
        alt = Path(".harness/methodologies/exploration/manifest.yaml")
        if alt.exists():
            manifest_path = alt
        else:
            print(f"ERROR: manifest not found at {MANIFEST} or {alt}",
                  file=sys.stderr)
            sys.exit(2)
    else:
        manifest_path = MANIFEST

    with manifest_path.open() as f:
        manifest = yaml.safe_load(f) or {}

    template_relaxations = manifest.get("relaxes_gates", []) or []
    spike_ids = active_spike_ids()

    relaxations = []
    for entry in template_relaxations:
        target = entry.get("target")
        reason = entry.get("reason", "")
        expanded_paths = []
        for p in entry.get("paths", []) or []:
            expanded_paths.extend(expand_paths(p, spike_ids))
        relaxations.append({
            "target": target,
            "paths": expanded_paths,
            "reason": reason,
        })

    out = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "active_spikes": spike_ids,
        "relaxations": relaxations,
    }

    RELAX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RELAX_FILE.open("w") as f:
        yaml.dump(out, f, sort_keys=False, allow_unicode=True)

    print(f"Wrote {RELAX_FILE} ({len(relaxations)} relaxation rules, "
          f"{len(spike_ids)} active spike(s))")


if __name__ == "__main__":
    main()
