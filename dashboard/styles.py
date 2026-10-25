"""Custom Taste Design System & Modern Dark Glassmorphism CSS for Streamlit Dashboard.

Adheres to enterprise SaaS UI/UX Pro Max standards:
- Deep Obsidian Void (#0B0F19)
- Slate Glass Surface (rgba(24, 32, 47, 0.75)) with backdrop-filter blur
- Electric Accents: Indigo (#6366F1), Violet (#8B5CF6), Cyan (#06B6D4)
- Google Font: Plus Jakarta Sans & Inter
- Pure Dark Chrome: Transparent Streamlit header (0 white glare), glowing segmented tabs
"""

from __future__ import annotations

import plotly.graph_objects as go

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* --- Root & Global Reset --- */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #F1F5F9;
}

.stApp {
    background-color: #0B0F19 !important;
    background-image: 
        radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.09) 0%, transparent 40%),
        radial-gradient(circle at 90% 25%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 50% 85%, rgba(6, 182, 212, 0.06) 0%, transparent 50%) !important;
    background-attachment: fixed !important;
}

/* Eliminate white top header and deploy banners */
header[data-testid="stHeader"], [data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
    z-index: 999990 !important;
}

/* Ensure toolbar is visible so the expand button can render */
[data-testid="stToolbar"] {
    display: flex !important;
    visibility: visible !important;
    background: transparent !important;
}

/* Sidebar Toggle Controls - Always prominent & visible */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 999999 !important;
    background: rgba(30, 41, 59, 0.95) !important;
    border: 1px solid rgba(99, 102, 241, 0.6) !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover {
    background: rgba(99, 102, 241, 0.35) !important;
    border-color: #6366F1 !important;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.5) !important;
    transform: translateY(-1px) !important;
}

[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg {
    fill: #F8FAFC !important;
    color: #F8FAFC !important;
    stroke: #F8FAFC !important;
}

/* Collapse button inside open sidebar */
[data-testid="stSidebarCollapseButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

[data-testid="stSidebarCollapseButton"]:hover {
    background: rgba(99, 102, 241, 0.3) !important;
    border-color: #6366F1 !important;
}

/* Hide clutter (deploy button, decoration, status widget) */
.stAppDeployButton,
[data-testid="stAppDeployButton"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    display: none !important;
}

/* Custom Sleek Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #0B0F19;
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.6);
}

/* --- High-Contrast Typography --- */
h1, h2, h3, h4, h5, h6 {
    color: #F8FAFC !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

p, span, label {
    color: #CBD5E1;
}

/* --- Hero Banner & Header --- */
.hero-container {
    padding: 16px 0 20px 0;
    margin-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.hero-title {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0 0 8px 0;
    background: linear-gradient(135deg, #FFFFFF 20%, #C7D2FE 60%, #38BDF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
    text-shadow: 0 4px 20px rgba(99, 102, 241, 0.2);
}

.hero-sub {
    font-size: 13px;
    color: #94A3B8;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34D399;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 9999px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.status-dot {
    width: 7px;
    height: 7px;
    background: #10B981;
    border-radius: 50%;
    box-shadow: 0 0 10px #10B981;
}

/* --- Glassmorphism KPI Cards --- */
.kpi-card {
    background: rgba(24, 32, 47, 0.65);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top: 2px solid rgba(99, 102, 241, 0.4);
    border-radius: 16px;
    padding: 20px 22px;
    box-shadow: 0 8px 28px -4px rgba(0, 0, 0, 0.5);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), 
                border-color 0.25s ease, 
                box-shadow 0.25s ease;
    height: 100%;
}

.kpi-card:hover {
    transform: translateY(-4px);
    border-color: rgba(99, 102, 241, 0.65);
    border-top-color: #6366F1;
    box-shadow: 0 14px 34px -4px rgba(99, 102, 241, 0.25);
}

.kpi-label {
    font-size: 11px;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 28px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.02em;
    margin-bottom: 4px;
    line-height: 1.15;
}

.kpi-subtext {
    font-size: 11.5px;
    color: #64748B;
    margin: 0;
}

/* --- Pro Max Segmented Glass Tabs --- */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(15, 23, 42, 0.75) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    padding: 6px 8px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    gap: 8px !important;
    margin-bottom: 24px !important;
    display: flex !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 10px !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 9px 18px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #F8FAFC !important;
    background: rgba(255, 255, 255, 0.06) !important;
}

.stTabs [aria-selected="true"] {
    color: #FFFFFF !important;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.35) 0%, rgba(139, 92, 246, 0.35) 100%) !important;
    border: 1px solid rgba(99, 102, 241, 0.55) !important;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.28) !important;
}

.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* --- Pro Max YouTube Learning Cards --- */
.yt-card {
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 16px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100%;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), 
                border-color 0.25s ease, 
                box-shadow 0.25s ease;
}

.yt-card:hover {
    transform: translateY(-5px);
    border-color: rgba(239, 68, 68, 0.45);
    box-shadow: 0 16px 36px -4px rgba(239, 68, 68, 0.22);
}

.yt-thumb-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #0F172A;
    overflow: hidden;
}

.yt-thumb {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.35s ease;
}

.yt-card:hover .yt-thumb {
    transform: scale(1.05);
}

.yt-skill-pill {
    position: absolute;
    top: 10px;
    left: 10px;
    background: rgba(15, 23, 42, 0.85);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(99, 102, 241, 0.5);
    color: #A5B4FC;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.yt-body {
    padding: 16px;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}

.yt-title {
    font-size: 13.5px;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0 0 8px 0;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 38px;
}

.yt-meta {
    font-size: 11.5px;
    color: #94A3B8;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.yt-btn {
    margin-top: auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 14px;
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.85) 0%, rgba(185, 28, 28, 0.85) 100%);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #FFFFFF !important;
    text-decoration: none !important;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(220, 38, 38, 0.25);
}

.yt-btn:hover {
    background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%);
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(220, 38, 38, 0.4);
}

/* --- Sidebar UI Pro Max --- */
[data-testid="stSidebar"] {
    background-color: #0E1320 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

/* Streamlit Inputs in Sidebar */
.stSelectbox > div > div, .stTextInput > div > div {
    background-color: rgba(24, 32, 47, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 10px !important;
    color: #F8FAFC !important;
}

.stSelectbox > div > div:hover, .stTextInput > div > div:hover {
    border-color: rgba(99, 102, 241, 0.5) !important;
}

.stButton > button {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%) !important;
    border: 1px solid rgba(99, 102, 241, 0.4) !important;
    color: #F8FAFC !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.35) 0%, rgba(6, 182, 212, 0.35) 100%) !important;
    border-color: rgba(99, 102, 241, 0.7) !important;
    transform: translateY(-1px) !important;
}

/* --- Dataframe Custom Style --- */
.stDataFrame {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background: rgba(24, 32, 47, 0.5) !important;
}
</style>
"""


def apply_dark_chart_theme(fig: go.Figure, height: int = 400) -> go.Figure:
    """Apply unified Dark Glassmorphism aesthetic to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(family="Plus Jakarta Sans, Inter, sans-serif", color="#CBD5E1", size=12),
        hoverlabel=dict(
            bgcolor="rgba(15, 23, 42, 0.95)",
            bordercolor="rgba(99, 102, 241, 0.5)",
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#FFFFFF", size=12),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            color="#94A3B8",
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            color="#94A3B8",
        ),
    )
    return fig


def humanize_number(count: int | float) -> str:
    """Format view/like counts into clean SaaS compact notation (e.g. 42M, 350K)."""
    val = float(count)
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M".replace(".0M", "M")
    if val >= 1_000:
        return f"{val / 1_000:.0f}K"
    return str(int(val))
