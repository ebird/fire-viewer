# R script to map species codes to species names using eBird taxonomy

library(jsonlite)
library(rebird)

# Set default input file
input_file <- "./schema.json"

# Read JSON file
schema <- fromJSON(input_file)

# Extract species codes
species_codes <- schema$species$species_code

# Get eBird taxonomy data
taxonomy <- rebird::ebirdtaxonomy()

# Create mapping: code -> species name
species_map <- setNames(
  lapply(species_codes, function(code) {
    match <- taxonomy[taxonomy$speciesCode == code, "comName"]
    if (length(match) != 1) NA else as.character(match)
  }),
  species_codes
)

# to JSON
cat(
  toJSON(species_map, pretty = TRUE, auto_unbox = TRUE),
  file = "./species_names.json"
)
