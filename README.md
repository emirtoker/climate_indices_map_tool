# Climate Indices Map Tool

Interactive web app for visualizing **64 climate and bio-climate indices** computed over Türkiye, built with Streamlit and Folium.

## What it does

Browse, filter, and overlay any of 64 climate indices on an interactive map of Türkiye. Choose color palettes, thresholds, opacities. Combine multiple indices into a single synthesis mask. Compare historical (1995–2014) with future projections (2041–2060 and 2081–2100) under three SSP scenarios.

## Data sources

Computed from 1 km daily CHELSA observed climatology (1995–2014) and from a 10-member ensemble of 0.5° daily GCMs projected to mid- and end-century under three SSP scenarios:

- **SSP126** — Low-Emission (sustainable, optimistic)
- **SSP245** — Intermediate (middle-of-the-road)
- **SSP585** — High-Emission (fossil-fueled, pessimistic)

Indices are organized into **Climate Indices** (Temperature, Precipitation, Drought, Energy, Agriculture) and **Bio-Climate Indices** (Human Comfort, Agriculture & Livestock, Atmospheric Comfort).

Full reference with formulas and units is inside the app's **About** panel.

## Run locally

```bash
git clone https://github.com/emirtoker/climate_indices_map_tool.git
cd climate_indices_map_tool

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
streamlit run app/main.py
```

## Project context

Developed within a TÜBİTAK BAP-funded research project on climate change impacts and adaptation in architecture for Türkiye.

## License

CC-BY-4.0 — share and adapt with attribution. See [LICENSE](LICENSE).
