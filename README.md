# Fire Response Species Maps

Static, JSON-driven viewer for species fire response map PNGs. Deployed via GitHub Pages.

## Features
- Two modes: view all variables for a species, or one variable across species.
- Species and variable filters with mutually exclusive selection.
- Direct PNG download buttons.
- Permalinks using query params (?species=CODE or ?variable=VAR_KEY).
- JSON Schema validation + URL link checking in CI before deploy.

## Data Schema
Data lives in `schema.json` and must satisfy `schema.spec.json`.

## Development
Open `index.html` directly (no build step) or serve with a simple static server.

## Adding / Updating Data
1. Update `schema.json` (ensure each species has exactly five image objects).
2. Commit and push to `main`.
3. GitHub Action validates JSON and links, then deploys.

## Validation Locally
```
pip install jsonschema
python scripts/validate_schema.py --links
```

## Deployment
Automatically published to the `gh-pages` branch by the workflow in `.github/workflows/deploy.yml`.