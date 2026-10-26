# Use of Python in Routing Problems

A thesis code repository accompanying the diploma thesis **Use of Python in Routing Problems**. The code demonstrates a reusable Python framework for classical logistics routing problems, with mixed-integer linear programming models solved using Gurobi.

## Models in this repository

- **TSP** — Travelling Salesman Problem
- **TSPTW** — Travelling Salesman Problem with Time Windows
- **VRP** — Vehicle Routing Problem
- **VRPTW** — Vehicle Routing Problem with Time Windows
- **CPP** — Chinese Postman Problem (arc routing)

The two unified scripts use Boolean configuration flags to activate capacity and time-window constraints. `unified_vrptw.py` is configured for the VRPTW example; `unified_tsptw.py` is configured for the TSPTW example. `chinese_postman.py` contains the separate CPP model.

## Repository contents

```text
src/
  unified_vrptw.py       Unified framework, configured for VRPTW
  unified_tsptw.py       Unified framework, configured for TSPTW
  chinese_postman.py    Chinese Postman Problem model
 data/
  README.md             Notes about the input files
```

## Requirements

- Python 3.10 or later
- Gurobi and a valid Gurobi license
- Python packages listed in `requirements.txt`
- Internet access for the unified routing scripts, which call Nominatim for geocoding and OSRM for road distance and duration matrices

## Prepare input files

The original scripts expect input workbooks in the repository's top-level folder:

- `input.xlsx` for the unified routing models. Expected columns: `ID`, `Name`, `Address`, `Demand`, `Ready`, `Due`, and `Service`.
- `edges.xlsx` for the Chinese Postman Problem. It should contain the weighted adjacency matrix, with the node labels in the first column.

Input workbooks and generated outputs are intentionally excluded from this repository draft. Add only data that you have permission to share. Do not commit personal addresses, confidential information, API keys, or other restricted data. The `.gitignore` file excludes the expected input and generated output files by default.

## Run

From the repository's top-level folder, after installing the requirements and placing permitted input workbooks there:

```bash
python src/unified_vrptw.py
python src/unified_tsptw.py
python src/chinese_postman.py
```

The unified scripts create route summaries, spreadsheets, maps, and visualisations. The Chinese Postman script creates a route result workbook and figure. Gurobi must be installed and licensed for the optimisation models to run.

## Thesis reference

Aysha Fahmi Kunnathery Mannanthara, *Use of Python in Routing Problems*, Diploma Thesis, Škoda Auto University, International Supply Chain Management and Procurement.

The full thesis PDF is not included in this code-focused draft. Add it only if you want it in the repository and have confirmed that you may share it publicly.

## License

No software license is included yet. Until a license is added, standard copyright applies and reuse is not automatically permitted. Choose a license only after confirming that it fits your university's and Gurobi-related terms.
