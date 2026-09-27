import os
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import numpy as np

os.makedirs("data/benchmarks", exist_ok=True)

# 1. Bar Chart
plt.figure(figsize=(6, 4))
plt.bar(['A', 'B', 'C'], [10, 20, 15], color='blue')
plt.title("Sample Bar Chart")
plt.xlabel("Category")
plt.ylabel("Values")
plt.savefig("data/benchmarks/bar_chart.png")
plt.close()

# 2. Pie Chart
plt.figure(figsize=(4, 4))
plt.pie([30, 70], labels=['Group 1', 'Group 2'], autopct='%1.1f%%')
plt.title("Sample Pie Chart")
plt.savefig("data/benchmarks/pie_chart.png")
plt.close()

# 3. Flowchart (using NetworkX)
plt.figure(figsize=(6, 4))
G = nx.DiGraph()
G.add_edges_from([("Start", "Process"), ("Process", "Decision"), ("Decision", "End"), ("Decision", "Process")])
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=2000, font_size=10, font_weight='bold')
plt.title("Sample Flowchart")
plt.savefig("data/benchmarks/flowchart.png")
plt.close()

# 4. Table (using Matplotlib table)
fig, ax = plt.subplots(figsize=(6, 2))
ax.axis('tight')
ax.axis('off')
df = pd.DataFrame(np.random.randint(0,100,size=(3, 3)), columns=list('ABC'))
ax.table(cellText=df.values, colLabels=df.columns, loc='center')
plt.savefig("data/benchmarks/table.png")
plt.close()

print("Generated benchmark images in data/benchmarks/")
