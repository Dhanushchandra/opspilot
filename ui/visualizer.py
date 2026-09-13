"""
High-Dimensional Vector Space and Workflow Visualizer for OpsPilot.
Provides 3D PCA vector space projections, cosine similarity geometry,
and interactive LangGraph state machine flowcharts.
"""

import numpy as np
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from typing import List, Dict, Any, Optional

from rag.pipeline import load_policy_documents, compute_embedding

# Cache document embeddings so PCA generation is instant (<50ms)
_cached_doc_embeddings = None
_cached_docs = None


def get_cached_knowledge_embeddings():
    global _cached_doc_embeddings, _cached_docs
    if _cached_doc_embeddings is not None and _cached_docs is not None:
        return _cached_docs, _cached_doc_embeddings

    docs = load_policy_documents()
    # If documents have multiple sections, we can treat each major section as a node
    chunks = []
    for d in docs:
        sections = d["text"].split("\n## ")
        for idx, sec in enumerate(sections):
            sec_text = sec if sec.startswith("#") else f"## {sec}"
            title = sec_text.splitlines()[0].replace("#", "").strip() if sec_text.splitlines() else d["id"]
            chunks.append({
                "id": f"{d['id']}_sec_{idx}",
                "doc_id": d["id"],
                "source": d["source"],
                "title": f"{d['title']} — {title}" if idx > 0 else d["title"],
                "text": sec_text.strip()
            })

    vectors = [compute_embedding(c["text"]) for c in chunks]
    _cached_docs = chunks
    _cached_doc_embeddings = np.array(vectors)
    return _cached_docs, _cached_doc_embeddings


def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    dot = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def generate_3d_vector_space_figure(query_text: Optional[str] = None) -> go.Figure:
    """
    Project high-dimensional embedding vectors (3072-D / 768-D) into an interactive 3D semantic space.
    Visualizes policy vectors, the user's query vector, and cosine similarity distance rays.
    """
    if not query_text or not str(query_text).strip():
        query_text = "Sales Account Executive onboarding and applications"

    docs, doc_vectors = get_cached_knowledge_embeddings()
    query_vector = np.array(compute_embedding(query_text))

    # Compute cosine similarity for each document chunk
    similarities = [compute_cosine_similarity(query_vector, dv) for dv in doc_vectors]

    # Combine all vectors for PCA projection down to 3 components
    all_vectors = np.vstack([doc_vectors, query_vector.reshape(1, -1)])
    n_samples = all_vectors.shape[0]

    n_components = min(3, n_samples)
    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(all_vectors)

    # Pad with zeros if fewer than 3 dimensions
    if coords.shape[1] < 3:
        padding = np.zeros((coords.shape[0], 3 - coords.shape[1]))
        coords = np.hstack([coords, padding])

    doc_coords = coords[:-1]
    query_coord = coords[-1]

    # Color palette based on policy domain
    palette = {
        "sales": "#10b981",       # Emerald
        "finance": "#06b6d4",     # Cyan
        "security": "#f59e0b",    # Amber
        "access": "#8b5cf6"       # Purple
    }

    fig = go.Figure()

    # 1. Plot Policy Nodes in 3D Space
    for idx, d in enumerate(docs):
        doc_id = d["doc_id"].lower()
        color = "#64748b"
        for k, col in palette.items():
            if k in doc_id:
                color = col
                break

        sim = similarities[idx]
        sim_pct = round(max(0.0, sim) * 100, 1)

        hover_text = (
            f"<b>{d['title']}</b><br>"
            f"Source: {d['source']}<br>"
            f"Semantic Relevance: <b>{sim_pct}%</b><br><br>"
            f"<i>{d['text'][:180]}...</i>"
        )

        # Draw node sphere
        fig.add_trace(go.Scatter3d(
            x=[doc_coords[idx, 0]],
            y=[doc_coords[idx, 1]],
            z=[doc_coords[idx, 2]],
            mode="markers+text",
            marker=dict(
                size=12 + (sim * 8),  # Higher similarity = larger node
                color=color,
                opacity=0.9,
                line=dict(color="#ffffff", width=1.5)
            ),
            text=[f"{d['doc_id']} ({sim_pct}%)"],
            textposition="top center",
            textfont=dict(size=10, color="#94a3b8"),
            hoverinfo="text",
            hovertext=hover_text,
            name=d["title"],
            showlegend=False
        ))

        # 2. Draw Distance Ray / Spring from Query to Node
        line_opacity = max(0.1, min(0.85, (sim - 0.2) / 0.8)) if sim > 0.2 else 0.08
        fig.add_trace(go.Scatter3d(
            x=[query_coord[0], doc_coords[idx, 0]],
            y=[query_coord[1], doc_coords[idx, 1]],
            z=[query_coord[2], doc_coords[idx, 2]],
            mode="lines",
            line=dict(
                color=color if sim > 0.45 else "#334155",
                width=3.5 if sim > 0.45 else 1.0
            ),
            opacity=line_opacity,
            hoverinfo="none",
            showlegend=False
        ))

    # 3. Plot the User Query Node (Glowing Diamond)
    query_hover = f"<b>User Request Embedding Vector</b><br>Query: '{query_text}'<br>Position: ({query_coord[0]:.2f}, {query_coord[1]:.2f}, {query_coord[2]:.2f})"
    fig.add_trace(go.Scatter3d(
        x=[query_coord[0]],
        y=[query_coord[1]],
        z=[query_coord[2]],
        mode="markers+text",
        marker=dict(
            size=18,
            symbol="diamond",
            color="#ef4444",
            line=dict(color="#fef08a", width=3)
        ),
        text=["[QUERY VECTOR]"],
        textposition="bottom center",
        textfont=dict(size=12, color="#f87171", family="sans-serif"),
        hoverinfo="text",
        hovertext=query_hover,
        name="User Request Vector",
        showlegend=True
    ))

    # Dark Space Nebula Styling
    fig.update_layout(
        title=dict(
            text="High-Dimensional Semantic Vector Space (3D PCA Projection of RAG Policy Clusters)",
            font=dict(color="#38bdf8", size=15)
        ),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        scene=dict(
            xaxis=dict(backgroundcolor="#0b0f19", gridcolor="#1e293b", showbackground=True, zerolinecolor="#334155", title="PC 1"),
            yaxis=dict(backgroundcolor="#0b0f19", gridcolor="#1e293b", showbackground=True, zerolinecolor="#334155", title="PC 2"),
            zaxis=dict(backgroundcolor="#0b0f19", gridcolor="#1e293b", showbackground=True, zerolinecolor="#334155", title="PC 3"),
            camera=dict(eye=dict(x=1.4, y=1.4, z=1.1))
        ),
        margin=dict(l=0, r=0, b=0, t=35),
        height=480,
        legend=dict(
            font=dict(color="#94a3b8"),
            bgcolor="rgba(15, 23, 42, 0.7)",
            bordercolor="#334155",
            borderwidth=1,
            x=0.02,
            y=0.98
        )
    )

    return fig


def generate_cosine_similarity_bar_chart(query_text: Optional[str] = None) -> go.Figure:
    """Generate ranking bar chart of cosine similarities for the current query."""
    if not query_text or not str(query_text).strip():
        query_text = "Sales Account Executive onboarding and applications"

    docs, doc_vectors = get_cached_knowledge_embeddings()
    query_vector = np.array(compute_embedding(query_text))

    scores = []
    for d, dv in zip(docs, doc_vectors):
        sim = compute_cosine_similarity(query_vector, dv)
        scores.append({
            "title": d["title"][:35],
            "score": max(0.0, sim) * 100,
            "source": d["source"]
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    top_scores = scores[:6]

    fig = go.Figure(go.Bar(
        x=[s["score"] for s in top_scores],
        y=[s["title"] for s in top_scores],
        orientation="h",
        marker=dict(
            color=[s["score"] for s in top_scores],
            colorscale="Blues",
            line=dict(color="#38bdf8", width=1)
        ),
        text=[f"{s['score']:.1f}%" for s in top_scores],
        textposition="auto",
        hovertext=[f"Source: {s['source']}" for s in top_scores]
    ))

    fig.update_layout(
        title=dict(text="Semantic Proximity Ranking (Cosine Similarity)", font=dict(color="#38bdf8", size=13)),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#0b0f19",
        xaxis=dict(range=[0, 100], gridcolor="#1e293b", zerolinecolor="#334155", ticksuffix="%", tickfont=dict(color="#94a3b8")),
        yaxis=dict(autorange="reversed", tickfont=dict(color="#cbd5e1", size=11)),
        margin=dict(l=10, r=20, b=25, t=35),
        height=220
    )
    return fig


def render_workflow_flowchart_html(trace: List[Dict[str, Any]], current_status: str) -> str:
    """
    Generate an interactive enterprise state graph of the LangGraph agent workflow.
    Active and completed nodes show telemetry badges and state indicators.
    """
    # LangGraph standard sequence
    nodes = [
        {"id": "START", "label": "Request Ingestion", "tag": "00 INGEST"},
        {"id": "Security Inspection", "label": "Security Guardrail", "tag": "01 SEC-GUARD"},
        {"id": "Employee Identification", "label": "Identity Resolution", "tag": "02 IAM-RESOLVE"},
        {"id": "Policy Context Retrieval", "label": "Policy RAG Context", "tag": "03 RAG-SEARCH"},
        {"id": "Current State Inspection", "label": "Current State & IAM", "tag": "04 STATE-AUDIT"},
        {"id": "Plan Generation", "label": "Workflow Planner", "tag": "05 PLANNER"},
        {"id": "Plan Validation", "label": "Catalog & Policy Gate", "tag": "06 VALIDATION"},
        {"id": "Privileged Guardrail", "label": "Approval Gate", "tag": "07 AUTH-GATE"},
        {"id": "Access Provisioning", "label": "Execute MCP & RPA", "tag": "08 EXECUTION"},
        {"id": "Entitlement Verification", "label": "Verify Entitlements", "tag": "09 VERIFICATION"},
        {"id": "ITSM Ticketing", "label": "ITSM Documentation", "tag": "10 ITSM-TICKET"},
        {"id": "END", "label": "Executive Summary", "tag": "11 SUMMARY"}
    ]

    trace_map = {t["step"]: t for t in trace}

    nodes_html = []
    for idx, node in enumerate(nodes):
        nid = node["id"]
        status = "NOT_REACHED"
        msg = "Pending execution"

        if nid == "START":
            status = "SUCCESS"
            msg = "Request received"
        elif nid == "END":
            status = "SUCCESS" if current_status == "COMPLETED" else ("WARNING" if "APPROVAL" in current_status or "CLARIFICATION" in current_status else "BLOCKED")
            msg = f"Status: {current_status}"
        else:
            for step_key, t in trace_map.items():
                if nid.lower() in step_key.lower() or step_key.lower() in nid.lower():
                    status = t["status"]
                    msg = t["message"][:80] + "..." if len(t["message"]) > 80 else t["message"]
                    break

        # Enterprise corporate styling per status
        glow_color = "#334155"
        border_color = "#334155"
        bg_color = "#0f172a"
        text_color = "#64748b"
        tag_bg = "#1e293b"
        tag_color = "#94a3b8"

        if status == "SUCCESS":
            glow_color = "rgba(16, 185, 129, 0.3)"
            border_color = "#10b981"
            bg_color = "#064e3b"
            text_color = "#34d399"
            tag_bg = "#047857"
            tag_color = "#ffffff"
        elif status == "WARNING":
            glow_color = "rgba(245, 158, 11, 0.3)"
            border_color = "#f59e0b"
            bg_color = "#78350f"
            text_color = "#fbbf24"
            tag_bg = "#b45309"
            tag_color = "#ffffff"
        elif status in ["BLOCKED", "FAILED"]:
            glow_color = "rgba(239, 68, 68, 0.4)"
            border_color = "#ef4444"
            bg_color = "#7f1d1d"
            text_color = "#f87171"
            tag_bg = "#b91c1c"
            tag_color = "#ffffff"
        elif status == "SKIPPED":
            glow_color = "rgba(148, 163, 184, 0.15)"
            border_color = "#475569"
            bg_color = "#1e293b"
            text_color = "#cbd5e1"
            tag_bg = "#334155"
            tag_color = "#cbd5e1"

        arrow = '<div style="color: #475569; font-weight: 700; font-size: 14px; margin: 0 5px;">→</div>' if idx < len(nodes) - 1 else ''

        card_html = (
            f'<div style="display:inline-flex;align-items:center;margin:4px 0;">'
            f'<div style="background:{bg_color};border:1px solid {border_color};box-shadow:0 0 8px {glow_color};border-radius:6px;padding:7px 12px;min-width:135px;text-align:center;">'
            f'<div style="font-family:monospace;font-size:10px;font-weight:700;background:{tag_bg};color:{tag_color};padding:2px 6px;border-radius:3px;display:inline-block;letter-spacing:0.5px;">{node["tag"]}</div>'
            f'<div style="font-weight:600;font-size:11px;color:{text_color};margin-top:4px;white-space:nowrap;">{node["label"]}</div>'
            f'<div style="font-size:9px;color:#94a3b8;margin-top:2px;letter-spacing:0.5px;text-transform:uppercase;">{status}</div>'
            f'</div>'
            f'{arrow}'
            f'</div>'
        )
        nodes_html.append(card_html)

    nodes_str = "".join(nodes_html)
    full_html = (
        f'<div style="background:#0b0f19;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;overflow-x:auto;white-space:nowrap;margin-bottom:12px;">'
        f'<div style="display:inline-flex;align-items:center;gap:3px;">'
        f'{nodes_str}'
        f'</div>'
        f'</div>'
    )
    return full_html
