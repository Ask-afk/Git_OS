#!/usr/bin/env python3
"""Build a Daywell tablet SD image on Linux, without mounting a disk device."""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parent
BASE_URL = "https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-10-06/2026-10-06-raspios-trixie-arm64.img.xz"
BASE_SHA = "976766570bee2aaf3047dd78649cfe82abb8fe9687b7f15030cd533ba4e9f7a9"


def unpack(base, prefix, root):
    with base.open("rb") as src:
        if hashlib.file_digest(src, "sha256").hexdigest() != BASE_SHA:
            raise ValueError("The base image checksum differs from the official release.")
    with lzma.open(base) as src, prefix.open("wb") as head, root.open("wb") as fs:
        first = src.read(512)
        offset = struct.unpack_from("<I", first, 446 + 16 + 8)[0] * 512
        head.write(first)
        remaining = offset - 512
        while remaining:
            block = src.read(min(4 << 20, remaining))
            if not block:
                raise ValueError("Incomplete boot partition")
            head.write(block)
            remaining -= len(block)
        while block := src.read(4 << 20):
            if block.count(0) == len(block):
                fs.seek(len(block), 1)
            else:
                fs.write(block)
        fs.truncate()


def customize(root, work):
    brand_source = (PROJECT / "ui/brand.js").read_text()
    brand = json.loads(re.search(r"window.TABLET_BRAND\s*=\s*(.*?);", brand_source).group(1))
    if not re.fullmatch(r"[\w .-]{1,48}", brand):
        raise ValueError("Use up to 48 letters, numbers, spaces, periods or hyphens for the brand.")

    def debug(command):
        proc = subprocess.run(["debugfs", "-w", "-R", command, root], capture_output=True, text=True, check=True)
        errors = "\n".join(proc.stderr.splitlines()[1:])
        if errors and "File not found by ext2_lookup" not in errors:
            raise RuntimeError(command + "\n" + errors)
        return proc.stdout

    def exists(path):
        return "Inode:" in debug("stat " + path)

    def directory(path):
        if path != "/" and not exists(path):
            directory(str(Path(path).parent))
            debug("mkdir " + path)
            debug("set_inode_field " + path + " mode 040755")

    def replace(path):
        directory(str(Path(path).parent))
        if exists(path):
            debug("rm " + path)

    def link(path, target):
        replace(path)
        debug(f"symlink {path} {target}")

    def install(src, dest, mode="0100644"):
        replace(dest)
        if '"' in str(src):
            raise ValueError("Build paths must not contain quotation marks.")
        debug(f'write "{src}" {dest}')
        debug(f"set_inode_field {dest} mode {mode}")
        if not exists(dest):
            raise RuntimeError("Failed to install " + dest)

    for src in (PROJECT / "ui").rglob("*"):
        if src.is_file():
            install(src, "/opt/daywell/ui/" + str(src.relative_to(PROJECT / "ui")))
    for name in ("autostart", "profile", "daywell-session", "rc.xml"):
        install(PROJECT / "linux" / name, "/opt/daywell/session/" + name, "0100755")
    for name in ("browser", "daywell-setup"):
        install(PROJECT / "linux" / name, "/opt/daywell/" + name, "0100755")
    install(PROJECT / "server.py", "/opt/daywell/server.py", "0100755")
    install(PROJECT / "linux/daywell-setup.service", "/etc/systemd/system/daywell-setup.service")
    install(PROJECT / "linux/daywell-server.service", "/etc/systemd/system/daywell-server.service")
    install(PROJECT / "linux/autologin.conf", "/etc/systemd/system/getty@tty1.service.d/zz-daywell.conf")
    # Use a real PAM login on the local seat. labwc is the only graphical session.
    link("/etc/systemd/system/default.target", "/usr/lib/systemd/system/multi-user.target")
    link("/etc/systemd/system/getty.target.wants/getty@tty1.service", "/usr/lib/systemd/system/getty@.service")
    link("/etc/systemd/system/multi-user.target.wants/daywell-server.service", "/etc/systemd/system/daywell-server.service")
    link("/etc/systemd/system/userconfig.service", "/dev/null")
    link("/etc/systemd/system/lightdm.service", "/dev/null")
    release = debug("cat /usr/lib/os-release")
    if "PRETTY_NAME=" not in release:
        raise ValueError("Could not read upstream OS identity")
    release = re.sub(r"^PRETTY_NAME=.*$", f'PRETTY_NAME="{brand} 1.0 (Raspberry Pi OS based)"', release, flags=re.M)
    release = re.sub(r"^NAME=.*$", f'NAME="{brand}"', release, flags=re.M)
    for filename, dest, content in [
        ("release", "/etc/os-release", release),
        ("issue", "/etc/issue", brand + " 1.0\n"),
        ("motd", "/etc/motd", brand + " touchscreen tablet\n"),
    ]:
        path = work / filename
        path.write_text(content)
        install(path, dest)
    subprocess.run(["e2fsck", "-fn", root], check=True)


def pack(prefix, root, out):
    out = out.resolve()
    # Publish the image only after compression succeeds.
    with tempfile.NamedTemporaryFile(dir=out.parent, delete=False) as tmp:
        partial = Path(tmp.name)
        try:
            with subprocess.Popen(["xz", "-1", "-T2", "-c"], stdin=subprocess.PIPE, stdout=tmp) as compress:
                for path in (prefix, root):
                    with path.open("rb") as src:
                        shutil.copyfileobj(src, compress.stdin, 4 << 20)
                compress.stdin.close()
                if compress.wait():
                    raise RuntimeError("Image compression failed")
            os.replace(partial, out)
        finally:
            partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path, help="Official 2026-10-06 Raspberry Pi OS desktop arm64 .img.xz")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new image filename.")
    with tempfile.TemporaryDirectory(dir=args.output.resolve().parent) as folder:
        work = Path(folder)
        prefix, root = work / "boot", work / "root"
        unpack(args.base, prefix, root)
        customize(root, work)
        pack(prefix, root, args.output)


if __name__ == "__main__":
    main()
