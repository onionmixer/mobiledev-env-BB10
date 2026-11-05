#!/usr/bin/env python3
"""Download and extract the simulator without executing its old installer."""
import concurrent.futures
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "emulator/config/simulator.lock.json").read_text())
ARCHIVE = ROOT / "emulator/downloads" / LOCK["file"]
PARTS = ROOT / "emulator/downloads" / (LOCK["file"] + ".chunks-1m")
DEST = ROOT / "emulator/images" / LOCK["version"]
CHUNK = 1024 * 1024


def digest(path, kind):
    h = hashlib.new(kind)
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def download():
    if ARCHIVE.exists():
        return
    PARTS.mkdir(parents=True, exist_ok=True)
    # Reuse complete 8 MiB ranges produced by earlier versions of this helper.
    legacy = ROOT / "emulator/downloads" / (LOCK["file"] + ".chunks")
    if legacy.exists():
        for old in legacy.glob("[0-9][0-9][0-9][0-9]"):
            first = int(old.name) * 8
            expected = min(8 * CHUNK, LOCK["bytes"] - first * CHUNK)
            if old.stat().st_size != expected:
                continue
            with old.open("rb") as data:
                for index in range(first, first + math.ceil(expected / CHUNK)):
                    block = data.read(CHUNK)
                    part = PARTS / f"{index:04d}"
                    if not part.exists():
                        part.write_bytes(block)

    def fetch(index):
        start = index * CHUNK
        end = min(start + CHUNK, LOCK["bytes"]) - 1
        size = end - start + 1
        part = PARTS / f"{index:04d}"
        if part.exists() and part.stat().st_size == size:
            return size
        tmp = part.with_suffix(".partial")
        for attempt in range(3):
            # A few mirrors/proxies return a cached complete HTTP 200 body for
            # a Range request. Refuse it and retry a distinct cache key.
            url = LOCK["url"] if attempt == 0 else LOCK["url"] + f"?bb10_range={start}_{attempt}"
            result = subprocess.run([
                "curl", "-L", "-sS", "--fail", "--retry", "1",
                "--connect-timeout", "20", "--max-time", "180",
                "--max-filesize", str(size), "--range", f"{start}-{end}",
                "--write-out", "%{http_code}", url, "-o", str(tmp),
            ], capture_output=True, text=True)
            if not result.returncode and result.stdout.strip() == "206" and tmp.exists() and tmp.stat().st_size == size:
                break
        else:
            raise RuntimeError(f"Range {index}: {result.stderr.strip()} HTTP {result.stdout.strip()}")
        tmp.replace(part)
        return size

    count = math.ceil(LOCK["bytes"] / CHUNK)
    done = 0
    errors = []
    reported = -1
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch, i) for i in range(count)]
        for future in concurrent.futures.as_completed(futures):
            try:
                done += future.result()
            except RuntimeError as error:
                errors.append(str(error))
                print(error, file=sys.stderr, flush=True)
                continue
            percent = int(done * 100 / LOCK["bytes"])
            if percent != reported:
                print(f"Download {percent}% ({done // (1024*1024)} MiB)", flush=True)
                reported = percent
    if errors:
        raise RuntimeError(f"{len(errors)} ranges failed; completed ranges are retained. Rerun setup to retry.")
    assembled = ARCHIVE.with_suffix(".assembling")
    with assembled.open("wb") as output:
        for i in range(count):
            with (PARTS / f"{i:04d}").open("rb") as part:
                shutil.copyfileobj(part, output, 1024 * 1024)
    if digest(assembled, "sha1") != LOCK["sha1"]:
        raise RuntimeError("Simulator SHA-1 mismatch; assembled file retained for inspection")
    assembled.replace(ARCHIVE)


class FileSlice(io.IOBase):
    """Seekable view of an uncompressed ZIP member, without a second GB copy."""
    def __init__(self, path, offset, size):
        self.file = path.open("rb")
        self.offset, self.size, self.pos = offset, size, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        new = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if new < 0:
            raise ValueError("negative seek")
        self.pos = new
        return new

    def read(self, size=-1):
        size = max(0, self.size - self.pos) if size < 0 else min(size, max(0, self.size-self.pos))
        self.file.seek(self.offset + self.pos)
        data = self.file.read(size)
        self.pos += len(data)
        return data

    def close(self):
        self.file.close()
        super().close()


def installer_entries(path):
    """Read InstallAnywhere's central directory, ignoring its nonstandard extra fields.

    Python ZipInfo rejects these legacy proprietary extras as malformed TLVs.
    The complete input is hash checked separately; sizes/offsets are bounded.
    """
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - 65557))
        tail = f.read()
        at = tail.rfind(b"PK\x05\x06")
        if at < 0 or at + 22 > len(tail):
            raise RuntimeError("Installer ZIP end record missing")
        end = struct.unpack_from("<4s4H2IH", tail, at)
        if end[1] or end[2] or end[3] != end[4] or end[4] == 65535:
            raise RuntimeError("Unsupported multi-disk/ZIP64 installer")
        end_abs = max(0, size - 65557) + at
        cd_size, cd_relative = end[5:7]
        cd_abs = end_abs - cd_size
        zip_base = cd_abs - cd_relative
        if zip_base < 0 or cd_abs < 0 or cd_size > 16 * 1024 * 1024:
            raise RuntimeError("Invalid installer ZIP directory bounds")
        f.seek(cd_abs)
        central = f.read(cd_size)
    entries, cursor = [], 0
    for _ in range(end[4]):
        if cursor + 46 > len(central) or central[cursor:cursor+4] != b"PK\x01\x02":
            raise RuntimeError("Invalid installer ZIP central directory")
        fields = struct.unpack_from("<4s6H3I5H2I", central, cursor)
        name_len, extra_len, comment_len = fields[10:13]
        record_end = cursor + 46 + name_len + extra_len + comment_len
        if record_end > len(central):
            raise RuntimeError("Truncated installer ZIP central directory")
        name = central[cursor+46:cursor+46+name_len].decode("utf-8")
        offset = zip_base + fields[16]
        if offset < zip_base or offset + 30 + fields[8] > cd_abs:
            raise RuntimeError("Invalid installer ZIP entry bounds")
        entries.append(SimpleNamespace(filename=name, compress_type=fields[4],
            file_size=fields[9], compress_size=fields[8], header_offset=offset))
        cursor = record_end
    return entries


def extract():
    if ARCHIVE.stat().st_size != LOCK["bytes"] or digest(ARCHIVE, "sha1") != LOCK["sha1"]:
        raise RuntimeError("Simulator archive length/SHA-1 mismatch")
    marker = DEST / "extraction.json"
    if marker.exists():
        print(f"Already extracted: {DEST}")
        return
    DEST.mkdir(parents=True, exist_ok=True)
    candidates = [i for i in installer_entries(ARCHIVE) if re.search(r"BlackBerry10Simulator[^/]*\.zip$", i.filename)]
    if len(candidates) != 1:
        raise RuntimeError("Expected one simulator ZIP inside installer")
    member = candidates[0]
    if member.compress_type != zipfile.ZIP_STORED or member.file_size != member.compress_size:
        raise RuntimeError("Simulator nested ZIP must be stored without compression")
    with ARCHIVE.open("rb") as f:
        f.seek(member.header_offset)
        header = f.read(30)
    if header[:4] != b"PK\x03\x04":
        raise RuntimeError("Invalid nested ZIP local header")
    name_len, extra_len = struct.unpack_from("<HH", header, 26)
    offset = member.header_offset + 30 + name_len + extra_len
    extracted = []
    with FileSlice(ARCHIVE, offset, member.file_size) as sliced, zipfile.ZipFile(sliced) as vmzip:
        for info in vmzip.infolist():
            if not re.fullmatch(r"BlackBerry10Simulator(?:-s\d{3})?\.(?:vmdk|vmx|vmxf|nvram|vmsd)", info.filename):
                continue
            path = DEST / info.filename
            partial = path.with_suffix(path.suffix + ".partial")
            print(f"Extract {info.filename} ({info.file_size} bytes)", flush=True)
            with vmzip.open(info) as src, partial.open("wb") as out:
                shutil.copyfileobj(src, out, 1024 * 1024)
            partial.replace(path)
            path.chmod(0o444)
            extracted.append({"file": info.filename, "bytes": info.file_size})
    marker.write_text(json.dumps({"source": LOCK, "sha256": digest(ARCHIVE, "sha256"),
                                  "files": extracted, "runtimeTested": False}, indent=2) + "\n")
    print(f"Simulator disk extracted: {DEST}")


if __name__ == "__main__":
    try:
        if "--extract-only" not in sys.argv:
            download()
        extract()
    except (OSError, RuntimeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"Simulator setup: {error}", file=sys.stderr)
        sys.exit(1)
