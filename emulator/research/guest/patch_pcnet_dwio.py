#!/usr/bin/env python3
"""Create a separate, hash-locked BB10 PCnet experiment; never edit the input.

The guest's DWORD writes after software reset assume DWIO remains enabled.
AMD's real device specifies clearing DWIO, so this is a BB10-specific
compatibility experiment, not a general correction to QEMU hardware behavior.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "emulator/runtime/qemu-system-x86_64"
OUTPUT = ROOT / "emulator/evidence/qemu-system-x86_64-bb10-pcnet"
EXPECTED = "ce36d097fd0954ba64462decd0b6ffc2d5448dcb843b76f3c535bfa790c21599"
OFFSET = 0x63FA50
BEFORE = bytes.fromhex("66 81 a3 70 21 00 00 7f ff")
AFTER = bytes.fromhex("66 81 a3 70 21 00 00 ff ff")


def main():
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED:
        raise SystemExit("Unsupported source binary; refusing to patch.")
    if original[OFFSET:OFFSET + len(BEFORE)] != BEFORE:
        raise SystemExit("Instruction mismatch; refusing to patch.")
    changed = bytearray(original)
    changed[OFFSET:OFFSET + len(BEFORE)] = AFTER
    assert sum(a != b for a, b in zip(original, changed)) == 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != changed:
            raise SystemExit('Existing output differs from this experiment; refusing to overwrite.')
    else:
        OUTPUT.write_bytes(changed)
    OUTPUT.chmod(0o755)
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": EXPECTED,
        "output": str(OUTPUT.relative_to(ROOT)),
        "outputSha256": hashlib.sha256(changed).hexdigest(),
        "functionVirtualAddress": "0x63fa00",
        "instructionFileOffset": hex(OFFSET),
        "before": BEFORE.hex(), "after": AFTER.hex(),
        "changedBytes": 1,
        "effect": "pcnet_s_reset preserves BCR18.DWIO; hard reset remains unchanged",
        "scope": "BB10 compatibility experiment, differs from AMD S_RESET specification",
        "sourceReference": "https://github.com/qemu/qemu/blob/v11.1.1/hw/net/pcnet.c",
    }
    current = ROOT / 'emulator/state/preparation/pcnet-current.json'
    current.parent.mkdir(parents=True, exist_ok=True)
    current.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
