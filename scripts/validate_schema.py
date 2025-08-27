#!/usr/bin/env python3
"""Validate schema.json against schema.spec.json and optionally perform link checks.
Usage: python scripts/validate_schema.py --links
Exits non-zero on failure.
"""
import argparse, json, sys, pathlib, time, concurrent.futures, urllib.request, urllib.error
from jsonschema import validate, Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / 'schema.json'
SPEC_FILE = ROOT / 'schema.spec.json'

HEADERS = {'User-Agent': 'FireMapsLinkChecker/1.0 (+https://github.com/)'}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def do_head(url, timeout=15):
    # Try HEAD then fallback to GET if method not allowed
    req = urllib.request.Request(url, method='HEAD', headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):  # method not allowed or forbidden, try GET
            try:
                req_get = urllib.request.Request(url, method='GET', headers=HEADERS)
                with urllib.request.urlopen(req_get, timeout=timeout) as resp:
                    return resp.status, None
            except Exception as ee:
                return getattr(ee, 'code', 0) or 0, str(ee)
        return e.code, str(e)
    except Exception as e:
        return 0, str(e)


def check_links(data, max_workers=10):
    urls = []
    for sp in data['species']:
        if 'zip_url' in sp:
            urls.append((sp['species_code']+':zip', sp['zip_url']))
        for img in sp['images']:
            urls.append((sp['species_code']+':'+img['file_name'], img['url']))
    results = []
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(do_head, url): (label, url) for label, url in urls}
        for fut in concurrent.futures.as_completed(fut_map):
            label, url = fut_map[fut]
            status, err = fut.result()
            results.append((label, url, status, err))
    duration = time.time() - start
    failures = [r for r in results if r[2] != 200]
    return results, failures, duration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--links', action='store_true', help='Also perform link checks')
    args = ap.parse_args()

    try:
        spec = load_json(SPEC_FILE)
        data = load_json(DATA_FILE)
    except Exception as e:
        print(f'ERROR: Failed to load JSON files: {e}', file=sys.stderr)
        return 2

    try:
        Draft202012Validator.check_schema(spec)
        validate(data, spec)
        print('Schema validation: OK')
    except Exception as e:
        print(f'Schema validation FAILED: {e}', file=sys.stderr)
        return 3

    if args.links:
        print('Checking links...')
        results, failures, duration = check_links(data)
        print(f'Checked {len(results)} URLs in {duration:.1f}s')
        if failures:
            print('Link failures:')
            for label, url, status, err in failures:
                print(f'  {label} -> {url} (status {status}) {err or ''}')
            return 4
        else:
            print('All links OK')
    return 0

if __name__ == '__main__':
    sys.exit(main())
