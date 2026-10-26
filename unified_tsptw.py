# =============================================================================
# UNIFIED ROUTING OPTIMISATION FRAMEWORK
# Solves: TSP, TSPTW, VRP, VRPTW
# Switch between models by changing the two flags below
# =============================================================================
 
# =========================================================
# 0. CONFIGURATION
# =========================================================
USE_CAPACITY     = False   # True -> VRP/VRPTW | False -> TSP/TSPTW
USE_TIME_WINDOWS = True  # True -> TSPTW/VRPTW | False -> TSP/VRP
DEPOT            = 0
STD_CAPACITY     = 20
 
# =========================================================
# 1. LOAD DATA
# =========================================================
import pandas as pd
import numpy as np
import requests
from geopy.geocoders import Nominatim
import time as time_module
from math import ceil
from gurobipy import Model, GRB, quicksum
 
df        = pd.read_excel("input.xlsx")
nodes     = df["ID"].tolist()
names     = dict(zip(df["ID"], df["Name"]))
addresses = df['Address'].tolist()
demand    = dict(zip(df["ID"], df["Demand"]))
 
if USE_TIME_WINDOWS:
    ready   = dict(zip(df["ID"], df["Ready"]))
    due     = dict(zip(df["ID"], df["Due"]))
    service = dict(zip(df["ID"], df["Service"]))
 
if USE_CAPACITY:
    total_demand = sum(v for k, v in demand.items() if k != DEPOT)
    num_vehicles = ceil(total_demand / STD_CAPACITY)
else:
    num_vehicles = 1
 
vehicles = list(range(num_vehicles))
print(f"Model : {'VRPTW' if USE_CAPACITY and USE_TIME_WINDOWS else 'VRP' if USE_CAPACITY else 'TSPTW' if USE_TIME_WINDOWS else 'TSP'}")
print(f"Nodes : {len(nodes)}  |  Vehicles : {num_vehicles}  |  Capacity : {STD_CAPACITY if USE_CAPACITY else 'N/A'}")
print("Data loaded.")
 
# =========================================================
# 2. GEOCODING
# =========================================================
geolocator = Nominatim(user_agent="unified_vrp")
coords = {}
for i in nodes:
    location = geolocator.geocode(addresses[i])
    if location is None:
        raise Exception(f"Geocoding failed for: {addresses[i]}")
    coords[i] = (location.latitude, location.longitude)
    time_module.sleep(1)
print("Geocoding done.")
 
# =========================================================
# 3. OSRM MATRICES
# =========================================================
coord_str = ";".join([f"{coords[i][1]},{coords[i][0]}" for i in nodes])
url = (f"http://router.project-osrm.org/table/v1/driving/"
       f"{coord_str}?annotations=distance,duration")
response    = requests.get(url).json()
dist_matrix = pd.DataFrame(response['distances'],
              index=addresses, columns=addresses) / 1000   # km
time_matrix = pd.DataFrame(response['durations'],
              index=addresses, columns=addresses) / 60     # minutes
 
with pd.ExcelWriter("DT_matrices.xlsx") as writer:
    dist_matrix.to_excel(writer, sheet_name="Distance_km")
    time_matrix.to_excel(writer, sheet_name="Time_min")
 
distance = dist_matrix.values   # c_ij  (NumPy)
travel   = time_matrix.values   # t_ij  (NumPy)
print("Matrices ready.")
 
# =========================================================
# 4. MODEL INITIALISATION AND DECISION VARIABLES
# =========================================================
model = Model("UnifiedRoutingFramework")
model.setParam("OutputFlag", 1)
 
# x[i,j,k]: 1 if vehicle k travels arc i->j
# self-loops excluded at definition so constraint summations
# mirror the mathematical formulation directly
arcs = [(i, j, k)
        for i in nodes
        for j in nodes
        for k in vehicles]
x = model.addVars(arcs, vtype=GRB.BINARY, name="x")
 
# T[i,k]: arrival time of vehicle k at node i (TSPTW/VRPTW only)
if USE_TIME_WINDOWS:
    T = model.addVars(nodes, vehicles, vtype=GRB.CONTINUOUS, name="T")
 
# u[i,k]: auxiliary variable for MTZ subtour elimination / load tracking
u = model.addVars(nodes, vehicles, vtype=GRB.CONTINUOUS, name="u")
 
# =========================================================
# 5. OBJECTIVE FUNCTION
# =========================================================
model.setObjective(
    quicksum(distance[i][j] * x[i, j, k] for i, j, k in arcs),
    GRB.MINIMIZE)
 
# =========================================================
# 6. ROUTING CONSTRAINTS
# =========================================================
customers = [i for i in nodes if i != DEPOT]
 
# each customer visited exactly once across all vehicles
for j in customers:
    model.addConstr(
        quicksum(x[i, j, k]
                 for i in nodes for k in vehicles
                 if (i, j, k) in arcs) == 1)
 
# each vehicle departs and returns to depot at most once
for k in vehicles:
    model.addConstr(
        quicksum(x[DEPOT, j, k] for j in customers
                 if (DEPOT, j, k) in arcs) <= 1)
    model.addConstr(
        quicksum(x[i, DEPOT, k] for i in customers
                 if (i, DEPOT, k) in arcs) <= 1)
 
# flow conservation per vehicle at each customer node
for k in vehicles:
    for j in customers:
        model.addConstr(
            quicksum(x[i, j, k] for i in nodes if (i, j, k) in arcs) ==
            quicksum(x[j, i, k] for i in nodes if (j, i, k) in arcs))
 
# =========================================================
# 7. CAPACITY CONSTRAINTS (VRP / VRPTW only)
# =========================================================
if USE_CAPACITY:
    for k in vehicles:
        model.addConstr(
            quicksum(demand[j] *
                     quicksum(x[i, j, k] for i in nodes
                              if (i, j, k) in arcs)
                     for j in customers) <= STD_CAPACITY)
 
# =========================================================
# 8. MTZ SUBTOUR ELIMINATION
# =========================================================
N = len(customers)
for k in vehicles:
    for i in nodes:
        for j in customers:          # depot excluded from j
            if i != DEPOT:
                if USE_CAPACITY:
                    # load-aware MTZ (VRP/VRPTW)
                    model.addConstr(
                        u[i, k] - u[j, k]
                        + STD_CAPACITY * x[i, j, k]
                        <= STD_CAPACITY - demand[j])
                else:
                    # pure subtour elimination (TSP/TSPTW)
                    model.addConstr(
                        u[i, k] - u[j, k]
                        + N * x[i, j, k] <= N - 1)
 
# =========================================================
# 9. TIME WINDOW CONSTRAINTS (TSPTW / VRPTW only)
# =========================================================
if USE_TIME_WINDOWS:
    M = 10000
    for k in vehicles:
        for i in nodes:
            model.addConstr(T[i, k] >= ready[i])
            model.addConstr(T[i, k] <= due[i])
        for i in nodes:
            for j in customers:      # propagation into depot excluded
                if i != j:
                    model.addConstr(
                        T[j, k] >= T[i, k] + service[i]
                        + travel[i][j]
                        - M * (1 - x[i, j, k]))
 
# =========================================================
# 10. OPTIMISATION
# =========================================================
model.optimize()
 
if model.Status != GRB.OPTIMAL:
    print(f"No optimal solution found. Status: {model.Status}")
    exit()
 
# =========================================================
# 11. ROUTE EXTRACTION
# =========================================================
routes = {k: [] for k in vehicles}
for i, j, k in arcs:
    if x[i, j, k].X > 0.5:
        routes[k].append((i, j))
 
# =========================================================
# 12. METRICS
# =========================================================
vehicle_distance = {}
vehicle_travel   = {}
total_distance = total_travel = 0
 
for k in vehicles:
    dist = sum(distance[i][j] for i, j in routes[k])
    trav = sum(travel[i][j]   for i, j in routes[k])
    vehicle_distance[k] = dist
    vehicle_travel[k]   = trav
    total_distance     += dist
    total_travel       += trav
 
# =========================================================
# 13. CONSOLE OUTPUT
# =========================================================
print("\n========== VEHICLE PERFORMANCE ==========")
for k in vehicles:
    print(f"\nVehicle {k}:")
    print(f"  Arcs     : {routes[k]}")
    print(f"  Distance : {vehicle_distance[k]:.2f} km")
    print(f"  Time     : {vehicle_travel[k]:.2f} min")
    if USE_CAPACITY:
        load = sum(demand[j] for j in customers
                   if any((i,j,k) in arcs and x[i,j,k].X > 0.5
                          for i in nodes))
        print(f"  Load     : {load} / {STD_CAPACITY}")
 
print("\n========== TOTAL SYSTEM PERFORMANCE ==========")
print(f"Total Distance : {round(total_distance, 2)} km")
print(f"Total Time     : {round(total_travel,   2)} min")
 
# =========================================================
# 14. EXCEL EXPORT (adaptive to active configuration)
# =========================================================
if   not USE_CAPACITY and not USE_TIME_WINDOWS:
    output_file = "TSP.xlsx"
elif not USE_CAPACITY and     USE_TIME_WINDOWS:
    output_file = "TSPTW.xlsx"
elif     USE_CAPACITY and not USE_TIME_WINDOWS:
    output_file = "VRP.xlsx"
else:
    output_file = "VRPTW.xlsx"
 
def minutes_to_hhmm(m):
    if m is None:
        return None
    return f"{int(m // 60):02d}:{int(m % 60):02d}"
 
# --- TIMELINE ---
timeline_data = []
for k in vehicles:
    current, order = DEPOT, 1
    while True:
        next_node = next(
            (j for j in nodes
             if (current, j, k) in arcs and x[current, j, k].X > 0.5),
            None)
        if next_node is None or next_node == DEPOT:
            break
        arrival = service_start = departure = None
        wait = 0
        if USE_TIME_WINDOWS:
            arrival       = T[next_node, k].X
            wait          = max(0, ready[next_node] - arrival)
            service_start = arrival + wait
            departure     = service_start + service[next_node]
        row = {
            "Vehicle":           k,
            "Order":             order,
            "From":              addresses[current],
            "To":                addresses[next_node],
            "Distance_km":       round(distance[current][next_node], 2),
            "Travel_Time_min":   round(travel[current][next_node],   2),
        }
        if USE_TIME_WINDOWS:
            row.update({
                "Arrival":       minutes_to_hhmm(arrival),
                "Wait_min":      round(wait, 2),
                "Service_Start": minutes_to_hhmm(service_start),
                "Departure":     minutes_to_hhmm(departure),
            })
        timeline_data.append(row)
        current = next_node
        order  += 1
 
# --- SUMMARY ---
summary_rows = []
for k in vehicles:
    row = {
        "Vehicle":               k,
        "Total_Distance_km":     round(vehicle_distance[k], 2),
        "Total_Travel_Time_min": round(vehicle_travel[k],   2),
    }
    if USE_TIME_WINDOWS:
        visited = [i for i in nodes
                   if any((i, j, k) in arcs and x[i, j, k].X > 0.5
                          for j in nodes)]
        op_time = (max(T[i, k].X for i in visited) -
                   min(T[i, k].X for i in visited)) if visited else None
        row["Operational_Time_min"] = round(op_time, 2) if op_time else None
    if USE_CAPACITY:
        row["Load_Used"] = sum(
            demand[j] for j in customers
            if any((i, j, k) in arcs and x[i, j, k].X > 0.5
                   for i in nodes))
    summary_rows.append(row)
 
# --- EDGES ---
edge_rows = [
    (k, i, j,
     round(distance[i][j], 2),
     round(travel[i][j],   2))
    for i, j, k in arcs if x[i, j, k].X > 0.5
]
 
# --- WRITE ---
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    pd.DataFrame(timeline_data).to_excel(
        writer, sheet_name="Timeline", index=False)
    pd.DataFrame(summary_rows).to_excel(
        writer, sheet_name="Summary",  index=False)
    pd.DataFrame(
        edge_rows,
        columns=["Vehicle", "From", "To",
                 "Distance_km", "Travel_Time_min"]
    ).to_excel(writer, sheet_name="Edges", index=False)
 
print(f"\nExport completed -> {output_file}")
 
# =========================================================
# 15. GOOGLE MAP VISUALISATION
# =========================================================
import folium
from folium.plugins import PolyLineTextPath
 
# reconstruct ordered node sequence per vehicle from arc list
ordered_routes = {}
for k in vehicles:
    current, route, visited = DEPOT, [DEPOT], set()
    while True:
        next_node = next(
            (j for i, j in routes[k]
             if i == current and j not in visited),
            None)
        if next_node is None:
            break
        route.append(next_node)
        visited.add(next_node)
        current = next_node
    ordered_routes[k] = route
 
m      = folium.Map(location=coords[nodes[0]], zoom_start=12)
colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred']
 
for idx, (k, route) in enumerate(ordered_routes.items()):
    color = colors[idx % len(colors)]
    for i in range(len(route) - 1):
        line = folium.PolyLine(
            locations=[coords[route[i]], coords[route[i + 1]]],
            color=color, weight=4, opacity=0.8,
            tooltip=f"V{k}: {names[route[i]]} -> {names[route[i+1]]}"
        ).add_to(m)
        PolyLineTextPath(
            line, '<', repeat=True, offset=7,
            attributes={'fill': color,
                        'font-size': '14',
                        'font-weight': 'bold'}
        ).add_to(m)
 
for i in nodes:
    folium.Marker(
        location=coords[i],
        icon=folium.DivIcon(html=(
            f'<div style="font-size:12px;font-weight:bold;color:black;'
            f'background:white;padding:2px 5px;border-radius:3px;'
            f'border:1px solid gray;white-space:nowrap;">'
            f'{names[i]}</div>')),
        popup=f"<b>{names[i]}</b><br>ID:{i}<br>Demand:{demand[i]}",
        tooltip=names[i]
    ).add_to(m)
 
map_file = output_file.replace(".xlsx", "_map.html")
m.save(map_file)
print(f"Map saved -> {map_file}")
 
# =========================================================
# 16. NETWORKX STATIC VISUALISATION
# =========================================================
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
 
G = nx.DiGraph()
for i, coord in coords.items():
    G.add_node(i, pos=coord)
 
colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred']
for idx, (k, route) in enumerate(ordered_routes.items()):
    color = colors[idx % len(colors)]
    for i in range(len(route) - 1):
        G.add_edge(route[i], route[i + 1], color=color, vehicle=k)
 
pos         = nx.get_node_attributes(G, 'pos')
edge_colors = [G[u][v]['color'] for u, v in G.edges()]
 
plt.figure(figsize=(10, 7))
nx.draw(G, pos,
        with_labels=True,
        node_size=400,
        node_color='skyblue',
        edge_color=edge_colors,
        arrowsize=15,
        font_size=9)
 
# title reflects active model
model_name = (
    "VRPTW" if USE_CAPACITY and USE_TIME_WINDOWS else
    "VRP"   if USE_CAPACITY else
    "TSPTW" if USE_TIME_WINDOWS else
    "TSP"
)
plt.title(f"Optimal {model_name} Route (NetworkX Visualization)")
 
# figure filename matches Excel and map filenames
figure_file = output_file.replace(".xlsx", ".png")
plt.savefig(figure_file, dpi=150, bbox_inches='tight')
plt.show()
print(f"Figure saved -> {figure_file}")
