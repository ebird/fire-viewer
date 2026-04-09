"""
Add github_url fields to schema.json for each image entry.

jsDelivr URL pattern:
  https://cdn.jsdelivr.net/gh/ebird/fire-viewer-images@main/images/{url-encoded filename}

Safe to re-run — existing github_url values are overwritten with the canonical URL.

Usage (from the fire-viewer project root):
  python3 scripts/add_github_urls.py
"""

import json
import urllib.parse
from pathlib import Path

REPO = "ebird/fire-viewer-images"
BRANCH = "main"
CDN_BASE = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/images"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.json"


def main():
    with open(SCHEMA_PATH) as f:
        data = json.load(f)

    count = 0
    for sp in data["species"]:
        for img in sp["images"]:
            encoded = urllib.parse.quote(img["file_name"])
            img["github_url"] = f"{CDN_BASE}/{encoded}"
            count += 1

    with open(SCHEMA_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Updated {count} image entries in {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
