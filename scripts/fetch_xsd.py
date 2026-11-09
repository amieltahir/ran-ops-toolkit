"""Fetch the 3GPP PM XSD (``measCollec.xsd``) into the gitignored ``third_party/``.

The XSD is not committed (check 3GPP copyright terms first). Give either a URL
to the XSD or to the TS 32.435 zip that contains it, or a local file:

    python scripts/fetch_xsd.py --url <url-to-xsd-or-zip>
    python scripts/fetch_xsd.py --file <path-to-xsd-or-zip>
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "third_party" / "measCollec.xsd"
XSD_NAME = "measCollec.xsd"


def extract_xsd(data: bytes) -> bytes:
    """Return XSD bytes from raw XSD content or a zip containing measCollec.xsd."""
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return data
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [
            n for n in archive.namelist() if Path(n).name.lower() == XSD_NAME.lower()
        ]
        if not names:
            raise SystemExit(
                f"{XSD_NAME} not found in zip; contents: {archive.namelist()}"
            )
        return archive.read(names[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    args = parser.parse_args()

    if args.url:
        with urllib.request.urlopen(args.url, timeout=60) as response:  # noqa: S310
            data = response.read()
    else:
        data = args.file.read_bytes()
    xsd = extract_xsd(data)
    if b"<xs:schema" not in xsd and b"<xsd:schema" not in xsd and b":schema" not in xsd:
        print("downloaded content does not look like an XSD", file=sys.stderr)
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(xsd)
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
