""" Generate JSON schema from a Figshare private link by scraping HTML and using file IDs. """

from typing import Optional
import requests
import json
import re
import time
from dataclasses import dataclass
from urllib.parse import unquote
import random

FIGSHARE_PRIVATE_LINK = "92ea9308ff2587864c49"
SHARED_URL = "https://figshare.com/s/92ea9308ff2587864c49"
FILE_BASE_URL = "https://figshare.com/ndownloader/files/"
SPECIES_MAP_FILE = "species_names.json"

@dataclass 
class FileInfo:
    file_id: str
    variable: str
    url: str
    file_name: Optional[str] = None
    species_code: Optional[str] = None
    variable2: Optional[str] = None

def parse_article_id_and_folder_structure(html):
    # Find article id
    article_id_match = re.search(r'/articles/(\d+)', html)
    article_id = article_id_match.group(1) if article_id_match else None
    # Find folderStructure JSON
    folder_match = re.search(r'"folderStructure":({.*?})', html, re.DOTALL)
    folder_json = folder_match.group(1) if folder_match else None
    folder_dict = json.loads(folder_json) if folder_json else {}
    return article_id, folder_dict

def refresh_waf_cookie(session: requests.Session, wait: float = 3.0) -> None:
    """Hit the main site to refresh AWS WAF tokens."""
    try:
        session.get("https://figshare.com/", timeout=10)
    except requests.RequestException:
        return
    time.sleep(wait)

def fetch_filename_for_fileid(file_id, session=None, max_retries=3):
    url = f"https://figshare.com/ndownloader/files/{file_id}?private_link={FIGSHARE_PRIVATE_LINK}"
    delay = 1
    get = session.get if session else requests.get
    for attempt in range(max_retries):
        with get(url, stream=True, allow_redirects=True, timeout=20) as resp:
            if resp.status_code == 200:
                cd = resp.headers.get("Content-Disposition", "")
                match = re.search(r'filename=\"?([^\";]+)\"?', cd)
                return unquote(match.group(1)) if match else None
            if resp.status_code == 202 and session is not None:
                print("Encountered WAF challenge, refreshing cookie...")
                refresh_waf_cookie(session, wait=random.uniform(2.5, 4.5))
            if attempt < max_retries - 1:
                print(f"Error {resp.status_code} for file_id {file_id}. Retrying in {delay} seconds...")
                time.sleep(delay + random.uniform(0.5, 1.5))
                delay *= 2
                continue
            print(f"Giving up on file_id {file_id} after {max_retries} attempts.")
            print(resp.text)
    return None

def main():
    # Step 1: Get HTML
    print("Fetching shared URL...")
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)"
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://figshare.com/",
        "Connection": "keep-alive",
    })
    session.get("https://figshare.com/", timeout=10)

    delay = 1
    for attempt in range(3):
        response = session.get(SHARED_URL, allow_redirects=True, timeout=20)
        if response.status_code == 200:
            break
        if response.status_code == 202:
            print(f"Received 202 Accepted (attempt {attempt + 1}). Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(f"Failed to fetch shared URL: {response.status_code}")
    else:
        raise RuntimeError("Failed to fetch shared URL after retries (status remained 202).")
    html = response.text

    # Step 2: Parse article id and folder structure
    print("Parsing HTML for article ID and folder structure...")
    article_id, folder_dict = parse_article_id_and_folder_structure(html)
    if not article_id:
        raise RuntimeError("Could not extract article id from HTML.")
    if not folder_dict:
        raise RuntimeError("Could not extract folder structure from HTML.")

    # Step 3: For each file id, get filename
    # This involves making a request per file id, so it may take a while
    print("Fetching filenames for each file ID...")
    fileid_to_filename = {}
    for index, (file_id, variable) in enumerate(folder_dict.items()):
        print(f"Getting filename for file ID {file_id} ({index + 1}/{len(folder_dict)})")
        # Figshare asks for no more than 1 per second
        # https://docs.figshare.com/#oai_pmh_rate_limit
        time.sleep(1.5 + random.uniform(0.5, 1.5))
        fname = fetch_filename_for_fileid(file_id, session=session)
        fileid_to_filename[file_id] = (fname, variable)


    # Step 4: Construct FileInfo objects
    # No network requests are made in this step, so it should be fast
    print("Creating FileInfo objects...")
    files = []
    for file_id, (fname, variable) in fileid_to_filename.items():
        url = f"{FILE_BASE_URL}{file_id}?private_link={FIGSHARE_PRIVATE_LINK}"
        f = FileInfo(file_id=file_id, variable=variable, url=url)
        if fname:
            f.file_name = fname
            if not fname.lower().endswith('.png'):
                print(f"Skipping non-PNG file ID {file_id}: {fname}")
                continue
            m = re.match(r'([^_]+)_(.+)\.png', fname)
            if not m:
                print(f"Filename does not match expected pattern: {fname}")
                continue
            species_code, variable2 = m.groups()
            f.species_code = species_code
            f.variable2 = variable2
        files.append(f)

    # Load species names mapping
    print("Loading species names mapping...")
    with open(SPECIES_MAP_FILE) as f:
        species_map = json.load(f)

    # Step 5: Build output schema
    print("Building output schema...")
    species_list = []
    unique_species = {f.species_code for f in files if f.species_code}
    for species in unique_species:
        species_files = [f for f in files if f.species_code == species]
        entry = {
            "species_code": species,
            "species_name": species_map.get(species, ""),
            "images": []
        }
        for f in species_files:
            entry["images"].append({
                "file_name": f.file_name,
                "label": f.variable2,
                "url": f.url
            })
        species_list.append(entry)

    # Final output with metadata
    output = {
        "source": SHARED_URL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "species": species_list,
    }

    with open("schema.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Wrote schema.json")

if __name__ == "__main__":
    main()
