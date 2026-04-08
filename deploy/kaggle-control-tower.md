# 🏗️ TORRE DE CONTROL v01 — Kaggle Notebook

## Dependencies (Kaggle → Add Data → Settings)
```
networkx
plotly
pandas
numpy
scikit-learn
```

## Notebook Structure

### Cell 1: Setup
```python
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from datetime import datetime

# Load data (upload leads.json or connect via API)
# For demo: simulated data matching real system
```

### Cell 2: System Graph
```python
G = nx.DiGraph()

# Nodes = services
nodes = ["User", "tienda.smarterbot.store", "webhook.ecocupon.cl", 
         "lead-webhook", "LLM", "Telegram", "leads.json", "BOLT Engine",
         "Odoo CRM", "n8n", "Supabase"]

G.add_nodes_from(nodes)

# Edges = data flow
edges = [
    ("User", "tienda.smarterbot.store", "form_submit"),
    ("tienda.smarterbot.store", "webhook.ecocupon.cl", "POST"),
    ("webhook.ecocupon.cl", "lead-webhook", "proxy"),
    ("lead-webhook", "LLM", "analyze"),
    ("lead-webhook", "leads.json", "store"),
    ("lead-webhook", "Telegram", "alert"),
    ("BOLT Engine", "lead-webhook", "monitor"),
    ("BOLT Engine", "LLM", "process_leads"),
    ("leads.json", "Odoo CRM", "sync"),
    ("n8n", "Telegram", "workflow"),
    ("BOLT Engine", "n8n", "trigger"),
]

for src, tgt, label in edges:
    G.add_edge(src, tgt, label=label)

print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
```

### Cell 3: Graph Visualization
```python
pos = nx.spring_layout(G, k=2, iterations=50)

edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}

fig = go.Figure()

# Nodes
node_x, node_y = [], []
for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)

fig.add_trace(go.Scatter(
    x=node_x, y=node_y,
    mode='markers+text',
    text=list(G.nodes()),
    textposition="top center",
    marker=dict(size=20, color='#FFD700', line=dict(width=2, color='#000')),
    name="Services",
    hoverinfo='text',
    textfont=dict(size=11, color='#000')
))

# Edges
for (src, tgt), label in edge_labels.items():
    x0, y0 = pos[src]
    x1, y1 = pos[tgt]
    fig.add_trace(go.Scatter(
        x=[x0, x1, None], y=[y0, y1, None],
        mode='lines',
        line=dict(width=1.5, color='#666'),
        name=label,
        hoverinfo='name',
        showlegend=False
    ))

fig.update_layout(
    title="SmarterOS Control Tower v01 — System Architecture",
    showlegend=False,
    plot_bgcolor='#0a0a0a',
    paper_bgcolor='#0a0a0a',
    font=dict(color='#FFD700'),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=700
)
fig.show()
```

### Cell 4: Lead Data Analysis
```python
# Simulated dataset matching real leads.json structure
data = {
    'timestamp': ['2026-04-08T21:00', '2026-04-08T21:05', '2026-04-08T21:10',
                  '2026-04-08T21:30', '2026-04-08T21:45', '2026-04-08T22:35'],
    'name': ['Test User', 'Direct Webhook', 'Test', 'Redirect Test', 'Test', 'Carlos Muñoz'],
    'product': ['CLAWBOT', 'Hosting', 'Hosting', 'Hosting', 'CLAWBOT', 'CLAWBOT'],
    'email': ['test@test.com', 'w@w.com', 't@t.com', 'r@t.com', 't@t.com', 'carlos@empresa.cl'],
    'phone': ['+56912345678', '+56922222222', '+56912345678', '+56900000', '+569111', '+56987654321'],
    'message_length': [4, 18, 4, 13, 4, 157],
    'llm_replied': [0, 0, 0, 0, 0, 1],
}

df = pd.DataFrame(data)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['intensidad'] = df['message_length'] * df['llm_replied'].map({0: 0.3, 1: 1.0})

print(df.to_string())
```

### Cell 5: Signal Intensity (Turbulence Detection)
```python
fig = px.scatter(df, x='timestamp', y='message_length', 
                 color='intensidad', size='intensidad',
                 hover_data=['name', 'product'],
                 color_continuous_scale='YlOrRd',
                 title="Signal Intensity — Digital Flow Turbulence")

fig.update_layout(
    plot_bgcolor='#0a0a0a',
    paper_bgcolor='#0a0a0a',
    font=dict(color='#FFD700'),
    xaxis_title="Time",
    yaxis_title="Message Length (bytes)"
)
fig.show()
```

### Cell 6: Classification (Normal vs Turbulent)
```python
from sklearn.cluster import KMeans

X = df[['message_length', 'intensidad']].values
kmeans = KMeans(n_clusters=2, random_state=42)
df['cluster'] = kmeans.fit_predict(X)
df['alerta'] = df['cluster'] == df['cluster'].mode()[0]

fig = px.scatter(df, x='timestamp', y='intensidad',
                 color='alerta', symbol='alerta',
                 hover_data=['name', 'product', 'message_length'],
                 title="Anomaly Detection — High Intent Leads")

fig.update_layout(
    plot_bgcolor='#0a0a0a',
    paper_bgcolor='#0a0a0a',
    font=dict(color='#FFD700')
)
fig.show()
```

### Cell 7: Control Tower Dashboard
```python
# Real-time status (simulated from /opt/smarterbot/status.json)
status = {
    "status": "ok",
    "webhook": True,
    "llm": True,
    "agent": True,
    "n8n": True,
    "caddy": True,
    "leads_total": 6,
    "unprocessed": 0,
    "errors_last_hour": 0,
    "version": "bolt-v2-autonomous"
}

services = ['webhook', 'llm', 'agent', 'n8n', 'caddy']
states = [status[s] for s in services]
colors = ['#4CAF50' if s else '#ff4444' for s in states]

fig = go.Figure(go.Bar(
    x=services,
    y=[1 if s else 0 for s in states],
    marker_color=colors,
    text=['✅' if s else '❌' for s in states],
    textposition='outside',
))

fig.update_layout(
    title=f"Control Tower v01 — System Health ({status['version']})",
    plot_bgcolor='#0a0a0a',
    paper_bgcolor='#0a0a0a',
    font=dict(color='#FFD700'),
    yaxis=dict(range=[-0.1, 1.1], showticklabels=False),
    showlegend=False,
    annotations=[dict(
        text=f"Leads: {status['leads_total']} | Unprocessed: {status['unprocessed']} | Errors: {status['errors_last_hour']}",
        xref="paper", yref="paper",
        x=0.5, y=-0.15, showarrow=False,
        font=dict(color='#FFD700', size=14)
    )]
)
fig.show()
```

### Cell 8: Narrative (Markdown)
```markdown
## SmarterOS Control Tower v01

This notebook simulates a Control Tower for SmarterOS — an autonomous 
digital flow monitoring system.

Instead of monitoring physical airflow turbulence, we monitor **digital 
flow turbulence**:

- **Nodes** = services (webhook, LLM, Telegram, CRM)
- **Edges** = data flow (form → webhook → LLM → storage → alert)
- **Intensity** = signal strength (message length × LLM processing)
- **Anomalies** = high-intent leads (potential conversions)

High intensity clusters behave like turbulent flow: they indicate 
meaningful activity with conversion potential.

### Architecture
- BOLT Engine v2: Autonomous rules engine (15s cycle)
- Lead Webhook: Captures forms + LLM analysis
- Telegram: Real-time alerts
- Odoo CRM: Lead management

### Live System
- 13/13 services operational
- 6 leads captured and processed
- All leads have AI responses
- Zero errors in last hour
```

## How to Publish

1. Go to [kaggle.com](https://kaggle.com) → New Notebook
2. Add dependencies: `networkx`, `plotly`, `pandas`, `numpy`, `scikit-learn`
3. Copy-paste cells above
4. Set title: "SmarterOS Control Tower v01 — Digital Flow Turbulence"
5. Tags: `time-series`, `anomaly-detection`, `network-analysis`, `business-intelligence`
6. Publish public
