# RouteWeave — Unified Routing Framework

> “Every stop is a connection. RouteWeave finds a smarter way to connect them.”

RouteWeave is an original Python framework I developed to bring several node-routing problems into one configurable optimisation workflow. Instead of treating each routing model as a separate program, the framework uses constraint switches to solve different versions of the problem and compare how those constraints affect a route.

The framework covers the Travelling Salesman Problem (TSP), TSP with Time Windows (TSPTW), Vehicle Routing Problem (VRP), and VRP with Time Windows (VRPTW). A separate Chinese Postman Problem (CPP) model demonstrates an arc-routing problem, where the goal is to cover required edges.

## What it does

- Selects a node-routing model by enabling or disabling vehicle-capacity and time-window constraints.
- Uses a Mixed-Integer Linear Programming formulation with Gurobi.
- Builds road distance and travel-time matrices through Nominatim and OSRM in the unified scripts.
- Exports route summaries, workbooks, maps, and visualisations.
- Includes a standalone CPP implementation using Gurobi and NetworkX.

## Repository structure

```text
src/
  unified_vrptw.py       Unified node-routing framework, configured for VRPTW
  unified_tsptw.py       Unified node-routing framework, configured for TSPTW
  chinese_postman.py    Standalone Chinese Postman Problem model
data/
  README.md             Input-data notes
```

## Requirements

- Python 3.10 or later
- Gurobi and a valid Gurobi license
- Python packages listed in `requirements.txt`
- Internet access for geocoding and road-network requests in the unified scripts

## Input files

The scripts expect workbooks in the repository's top-level folder:

- `input.xlsx` for the unified framework, with columns `ID`, `Name`, `Address`, `Demand`, `Ready`, `Due`, and `Service`.
- `edges.xlsx` for the CPP model, containing a weighted adjacency matrix with node labels in the first column.

Input datasets and generated outputs are excluded from this repository draft. Add only data you have permission to share. Review location data carefully before making a repository public. The `.gitignore` file excludes the expected local input and generated output files by default.

## Run

From the repository's top-level folder, after installing the requirements and placing permitted input workbooks there:

```bash
python src/unified_vrptw.py
python src/unified_tsptw.py
python src/chinese_postman.py
```

Gurobi must be installed and licensed for the optimisation models to run.

## Project note

RouteWeave is presented here as a standalone software project. The focus is the unified routing framework and how configurable constraints connect to practical route optimisation.

## License

No software license is included yet. Until a license is added, standard copyright applies and reuse is not automatically permitted. Choose a license only after confirming that it fits the terms for the code and solver used.
