""" Generate JSON schema from a directory of results. """

# Validate the format of the input data.
# It is a directory of directories, each representing a species.
# Each species directory contains a csv and multiple png files.

# Each species entry in the output schema looks like:
# {
# "zip_url": "{species.zip_url}",
# "species_code": "{species.code}",
# "species_name": "{species.common_name}",
# "images": [
#     {
#         "file_name": "{species.code}_burn_yr_fdis.png",
#         "label": "Variation in time since fire",
#         "url": "{species.burn_yr_fdis_url}"
#     },
#     {
#         "file_name": "{species.code}_PI_occurrence.png",
#         "label": "occurrence rPI",
#         "url": "{species.pi_occurrence_url}"
#     },
#     {
#         "file_name": "{species.code}_prop_fire_10y.png",
#         "label": "% high severity fire",
#         "url": "{species.prop_fire_10y_url}"
#     },
#     {
#         "file_name": "{species.code}_prop_fire_25y.png",
#         "label": "% burned (last 25y)",
#         "url": "{species.prop_fire_25y_url}"
#     },
#     {
#         "file_name": "{species.code}_severity_fdis.png",
#         "label": "Variation in fire severity",
#         "url": "{species.severity_fdis_url}"
#     }
# ]
# }

# So the input data we need for each species is:
# - species.code -- from directory name
# - species.common_name -- from csv file (column 'common_name', first row)
# - species.zip_url
# - species.burn_yr_fdis_url
# - species.pi_occurrence_url
# - species.prop_fire_10y_url
# - species.prop_fire_25y_url
# - species.severity_fdis_url
# The URLs will need to come from somewhere else, let's say a CSV file with columns:
# species_code, {each of the above URL fields}

import argparse
import csv
import json
from pathlib import Path

parser = argparse.ArgumentParser(description="Generate schema from a directory of results.")
parser.add_argument("input_dir", type=str, help="Input directory containing species directories.")
parser.add_argument("output_file", type=str, help="Output schema file.")
args = parser.parse_args()

# All contents of the input directory should be directories.
input_path = Path(args.input_dir)
if not input_path.is_dir():
    raise ValueError(f"Input path {input_path} is not a directory.")
species_dirs = [d for d in input_path.iterdir()]

output_data = {"species": []}

# Process each species directory.
for species_dir in species_dirs:

    # Check for CSV file and read common_name
    plotting_csv = species_dir / f"{species_dir.name}_plotting.csv"
    if not plotting_csv.is_file():
        raise ValueError(f"Missing expected CSV file: {plotting_csv}")
    with plotting_csv.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise ValueError(f"CSV file {plotting_csv} is empty.")
        common_name = rows[0].get("common_name")
        if not common_name:
            raise ValueError(f"CSV file {plotting_csv} missing 'common_name' column or it's empty.")

    # Check for links JSON file and read URLs
    links_json = species_dir / f"{species_dir.name}_links.json"
    if not links_json.is_file():
        raise ValueError(f"Missing expected links JSON file: {links_json}")
    with links_json.open() as f:
        links = json.load(f)
        assert isinstance(links, dict), f"Links JSON {links_json} is not a dictionary."
        required_keys = [
            "zip_url",
            "burn_yr_fdis_url",
            "pi_occurrence_url",
            "prop_fire_10y_url",
            "prop_fire_25y_url",
            "severity_fdis_url"
        ]
        for key in required_keys:
            if key not in links:
                raise ValueError(f"Links JSON {links_json} missing required key: {key}")

    # Check for expected PNG files
    expected_pngs = [
        species_dir / f"{species_dir.name}_burn_yr_fdis.png",
        species_dir / f"{species_dir.name}_PI_occurrence.png",
        species_dir / f"{species_dir.name}_prop_fire_10y.png",
        species_dir / f"{species_dir.name}_prop_fire_25y.png",
        species_dir / f"{species_dir.name}_severity_fdis.png",
    ]
    for png in expected_pngs:
        if not png.is_file():
            raise ValueError(f"Missing expected PNG file: {png}")

    # Construct species entry
    species_entry = {
        "zip_url": links["zip_url"],
        "species_code": species_dir.name,
        "species_name": common_name,
        "images": [
            {
                "file_name": f"{species_dir.name}_burn_yr_fdis.png",
                "label": "Variation in time since fire",
                "url": links["burn_yr_fdis_url"]
            },
            {
                "file_name": f"{species_dir.name}_PI_occurrence.png",
                "label": "occurrence rPI",
                "url": links["pi_occurrence_url"]
            },
            {
                "file_name": f"{species_dir.name}_prop_fire_10y.png",
                "label": "% high severity fire",
                "url": links["prop_fire_10y_url"]
            },
            {
                "file_name": f"{species_dir.name}_prop_fire_25y.png",
                "label": "% burned (last 25y)",
                "url": links["prop_fire_25y_url"]
            },
            {
                "file_name": f"{species_dir.name}_severity_fdis.png",
                "label": "Variation in fire severity",
                "url": links["severity_fdis_url"]
            }
        ]
    }
    output_data["species"].append(species_entry)

# Write output to JSON file
with open(args.output_file, "w") as f:
    json.dump(output_data, f, indent=2)
