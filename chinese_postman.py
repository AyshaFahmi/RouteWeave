
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from gurobipy import Model, GRB, quicksum
 
# =============================================================================
# STEP 1: Load Input Data from Excel
# =============================================================================
 
df    = pd.read_excel("edges.xlsx", index_col=0)
nodes = list(df.index)
M_BIG = 1000   # sentinel value indicating no direct edge exists
 
# extract real edges where weight < M_BIG
edges = []
for i in nodes:
    for j in nodes:
        if df.loc[i, j] < M_BIG:
            edges.append((i, j, df.loc[i, j]))
 
print(f"Nodes: {nodes}")
print(f"Edges found: {len(edges)}")
for e in edges:
    print(f"  {e[0]} -- {e[1]} : {e[2]}m")
 
# =============================================================================
# STEP 2: Build Cost and Requirement Matrices
# =============================================================================
 
c = {}    # c[i][j]: traversal cost of edge (i,j)
r = {}    # r[i][j]: 1 if edge (i,j) exists in E, 0 otherwise
 
for i in nodes:
    c[i] = {j: 0 for j in nodes}
    r[i] = {j: 0 for j in nodes}
 
for i, j, dist in edges:
    c[i][j] = dist
    c[j][i] = dist     # undirected: c_ij = c_ji
    r[i][j] = 1
    r[j][i] = 1        # undirected: requirement is symmetric
 
# =============================================================================
# STEP 3: Gurobi Model Initialisation and Decision Variables
# =============================================================================
 
model = Model("CPP")
model.setParam('OutputFlag', 1)   # show solver log
 
# arcs: all ordered pairs (i,j) where edge exists in E
arcs = [(i, j) for i in nodes for j in nodes if r[i][j] == 1]
x    = model.addVars(arcs, vtype=GRB.INTEGER, lb=0, name="x")
 
# =============================================================================
# STEP 4: Objective Function
# =============================================================================
 
model.setObjective(
    quicksum(c[i][j] * x[i, j] for i, j in arcs),
    GRB.MINIMIZE)
 
# =============================================================================
# STEP 5: Constraints
# =============================================================================
 
# edge coverage: x_ij + x_ji >= r_ij, for all (i,j) in E
covered = set()
for i, j, _ in edges:
    if (i, j) not in covered and (j, i) not in covered:
        model.addConstr(x[i, j] + x[j, i] >= r[i][j])
        covered.add((i, j))
 
# flow continuity: sum_j x_ij = sum_j x_ji, for all i in V
for i in nodes:
    model.addConstr(
        quicksum(x[i, j] for j in nodes if (i, j) in arcs) ==
        quicksum(x[j, i] for j in nodes if (j, i) in arcs))
 
# =============================================================================
# STEP 6: Solve
# =============================================================================
 
model.optimize()
 
if model.Status != GRB.OPTIMAL:
    print("No optimal solution found. Status:", model.Status)
    exit()
 
# =============================================================================
# STEP 7: Extract Traversal Solution
# =============================================================================
 
traversal = {(i, j): int(round(x[i, j].X))
             for i, j in arcs if x[i, j].X > 0.5}
 
print("\n--- Traversal Solution ---")
for (i, j), count in sorted(traversal.items()):
    print(f"  Arc {i} -> {j} : {count} traversal(s), cost = {c[i][j]}m")
 
total_distance = model.ObjVal
print(f"\nTotal traversal distance: {total_distance}m")
 
# =============================================================================
# STEP 8: Route Reconstruction (Eulerian Circuit)
# =============================================================================
 
MG = nx.MultiDiGraph()
for (i, j), count in traversal.items():
    for _ in range(count):
        MG.add_edge(i, j, weight=c[i][j])
 
start_node    = nodes[0]
euler_circuit = list(nx.eulerian_circuit(MG, source=start_node))
ordered_route = [start_node] + [j for i, j in euler_circuit]
 
print("\n--- Optimal Route ---")
print(" -> ".join(str(n) for n in ordered_route))
 
# =============================================================================
# STEP 9: Export Results to Excel
# =============================================================================
 
rows = [(i, j, c[i][j], traversal[(i, j)])
        for (i, j) in traversal]
df_traversal = pd.DataFrame(rows,
    columns=["From", "To", "Distance_m", "Traversals"])
df_traversal.to_excel("output_cpp.xlsx", index=False)
 
df_summary = pd.DataFrame([{
    "Total_Distance_m": total_distance,
    "Edges_in_E":       len(edges),
    "Total_Traversals": sum(traversal.values())}])
with pd.ExcelWriter("output_cpp.xlsx", mode="a") as writer:
    df_summary.to_excel(writer, sheet_name="Summary", index=False)
 
print("\nResults exported to output_cpp.xlsx")
 
# =============================================================================
# STEP 10: Visualisation
# =============================================================================
 
G = nx.Graph()
for i, j, dist in edges:
    G.add_edge(i, j, weight=dist)
 
pos = nx.spring_layout(G, seed=42)
 
edge_widths = []
for i, j in G.edges():
    count = traversal.get((i, j), traversal.get((j, i), 0))
    edge_widths.append(1 + 2 * count)
 
edge_labels = {(i, j): f"{G[i][j]['weight']}m" for i, j in G.edges()}
 
plt.figure(figsize=(10, 7))
nx.draw(G, pos, with_labels=True,
        node_size=500,
        node_color='skyblue',
        width=edge_widths,
        edge_color='red',
        font_size=10)
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
plt.title("Optimal CPP Route (NetworkX Visualization)\nEdge width proportional to traversal count")
plt.savefig("CPP.png", dpi=150, bbox_inches='tight')
plt.show()
print("Visualisation saved to CPP.png")
