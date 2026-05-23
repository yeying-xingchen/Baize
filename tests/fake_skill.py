from __future__ import annotations


def run(step, metadata):
    return f"skill {metadata['name']} handled {step.id}"
