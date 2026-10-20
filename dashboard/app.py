"""Indo Tech Job Market & YouTube Learning Radar - Streamlit Web Dashboard.

Built with Modern Dark Glassmorphism Design System, DuckDB in-memory caching,
and responsive analytics over the Gold Kimball Medallion Layer.
"""

import sys
from pathlib import Path

# Add project root to sys.path for standalone streamlit execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.queries import (
    get_filter_options,
    get_jobs_explorer,
    get_kpis,
    get_role_distribution,
    get_salary_insights,
    get_top_skills,
    get_work_policy_distribution,
    get_youtube_radar,
)
from dashboard.styles import CUSTOM_CSS, apply_dark_chart_theme, humanize_number

# --- 1. Page Configuration & Aesthetic Injection ---
st.set_page_config(
    page_title="JOSE | Indo Tech Job Market & Learning Radar",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- 2. Sidebar Filters ---
st.sidebar.markdown(
    """
    <div style="padding: 10px 0 16px 0;">
        <span style="font-size: 20px; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(135deg, #6366F1, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">JOSE RADAR</span>
        <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">Indo Tech Job & YouTube Learning Radar</div>
    </div>
    """,
    unsafe_allow_html=True,
)

filters = get_filter_options()

role_options = ["All Roles"] + filters.get("roles", [])
selected_role = st.sidebar.selectbox("Role Category", options=role_options)

policy_options = ["All Policies"] + filters.get("work_policies", [])
selected_policy = st.sidebar.selectbox("Work Policy", options=policy_options)

type_options = ["All Types"] + filters.get("employment_types", ["Full-Time", "Contract", "Internship"])
selected_type = st.sidebar.selectbox("Employment Type", options=type_options)

skill_options = ["All Skills"] + filters.get("skills", [])
selected_skill = st.sidebar.selectbox("Tech Skill", options=skill_options)

search_keyword = st.sidebar.text_input("Cari Posisi atau Perusahaan", placeholder="Contoh: intern, Data Engineer, GoTo...")

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Cache", width="stretch"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(
    """
    <div style="margin-top: 20px; font-size: 11px; color: #64748B;">
        <b>Arsitektur:</b> Serverless Lakehouse<br/>
        <b>Engine:</b> DuckDB 1.1 + dbt-core<br/>
        <b>Cost:</b> $0 Cloud Compute
    </div>
    """,
    unsafe_allow_html=True,
)

# --- 3. Hero Header ---
st.markdown(
    """
    <div class="hero-container">
        <h1 class="hero-title">Indo Tech Job Market & Learning Radar</h1>
        <div class="hero-sub">
            <span class="status-pill"><span class="status-dot"></span> Serverless Lakehouse Active</span>
            <span>Kimball Star Schema • Gold Layer DuckDB • $0 Cloud Compute</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- 4. Glassmorphism KPI Banner ---
kpis = get_kpis()

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

with kpi_col1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Lowongan Aktif</div>
            <div class="kpi-value">{kpis['total_jobs']:,}</div>
            <p class="kpi-subtext">Glints & JobStreet ID</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi_col2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Perusahaan Merekrut</div>
            <div class="kpi-value">{kpis['total_companies']:,}</div>
            <p class="kpi-subtext">SCD Type 2 Tracked</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi_col3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Peluang Remote</div>
            <div class="kpi-value">{kpis['remote_pct']}%</div>
            <p class="kpi-subtext">Work-from-Anywhere</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi_col4:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Skill Terpopuler</div>
            <div class="kpi-value">{kpis['top_skill']}</div>
            <p class="kpi-subtext">{kpis['top_skill_count']} Lowongan Memerlukan</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi_col5:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Video Pembelajaran</div>
            <div class="kpi-value">{kpis['total_videos']:,}</div>
            <p class="kpi-subtext">Tutorial Terkurasi</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- 5. Interactive Navigation Tabs ---
tab_demand, tab_learning, tab_explorer, tab_arch = st.tabs(
    [
        "Market Demand & Skill Radar",
        "YouTube Learning Radar",
        "Job Explorer & Salary Radar",
        "Lakehouse Architecture & Kimball",
    ]
)

# === TAB 1: MARKET DEMAND & SKILL RADAR ===
with tab_demand:
    col_chart_left, col_chart_right = st.columns([3, 2])

    with col_chart_left:
        st.markdown(
            "### Top 15 In-Demand Tech Skills",
            help="Jumlah lowongan kerja di Indonesia yang mensyaratkan teknologi ini.",
        )
        df_skills = get_top_skills(
            limit=15,
            role_filter=selected_role,
            work_policy_filter=selected_policy,
        )

        if not df_skills.empty:
            # Sort ascending for horizontal bar display
            df_plot = df_skills.sort_values(by="job_count", ascending=True)

            fig_skills = px.bar(
                df_plot,
                x="job_count",
                y="skill_name",
                orientation="h",
                color="job_count",
                color_continuous_scale=[
                    [0.0, "#4F46E5"],
                    [0.5, "#8B5CF6"],
                    [1.0, "#06B6D4"],
                ],
                labels={"job_count": "Jumlah Lowongan", "skill_name": "Tech Skill"},
            )
            fig_skills.update_layout(coloraxis_showscale=False)
            fig_skills.update_traces(
                text=df_plot["job_count"],
                textposition="outside",
                marker_line_width=0,
                hovertemplate="<b>%{y}</b><br>Demand: %{x} lowongan<extra></extra>",
            )
            apply_dark_chart_theme(fig_skills, height=450)
            st.plotly_chart(fig_skills, width="stretch")
        else:
            st.info("Tidak ada data skill yang sesuai dengan filter yang dipilih.")

    with col_chart_right:
        st.markdown("### Work Policy Distribution")
        df_policy = get_work_policy_distribution()
        if not df_policy.empty:
            color_map = {
                "Remote": "#10B981",
                "Hybrid": "#F59E0B",
                "WFO": "#64748B",
            }
            colors = [color_map.get(p, "#8B5CF6") for p in df_policy["work_policy"]]

            fig_policy = go.Figure(
                data=[
                    go.Pie(
                        labels=df_policy["work_policy"],
                        values=df_policy["total_jobs"],
                        hole=0.55,
                        marker=dict(colors=colors),
                        textinfo="label+percent",
                        hovertemplate="<b>%{label}</b><br>%{value} lowongan (%{percent})<extra></extra>",
                    )
                ]
            )
            fig_policy.update_layout(showlegend=False)
            apply_dark_chart_theme(fig_policy, height=210)
            st.plotly_chart(fig_policy, width="stretch")

        st.markdown("### Roles Breakdown")
        df_roles = get_role_distribution()
        if not df_roles.empty:
            fig_roles = px.bar(
                df_roles,
                x="role_category",
                y="total_postings",
                color_discrete_sequence=["#6366F1"],
                labels={"role_category": "Kategori Role", "total_postings": "Lowongan"},
            )
            fig_roles.update_traces(
                hovertemplate="<b>%{x}</b><br>%{y} lowongan<extra></extra>"
            )
            apply_dark_chart_theme(fig_roles, height=210)
            fig_roles.update_xaxes(tickangle=-25)
            st.plotly_chart(fig_roles, width="stretch")


# === TAB 2: YOUTUBE LEARNING RADAR ===
with tab_learning:
    st.markdown(
        """
        ### Interactive Learning Recommendations
        Video tutorial terkurasi dari YouTube yang dipetakan secara otomatis dengan **Top Tech Skills** yang paling banyak dibutuhkan di pasar kerja Indonesia.
        """
    )

    # Determine skills to recommend
    target_skills: list[str] = []
    if selected_skill and selected_skill != "All Skills":
        target_skills = [selected_skill]
    else:
        # Default to top 6 skills
        top_s_df = get_top_skills(limit=8)
        if not top_s_df.empty:
            target_skills = top_s_df["skill_name"].tolist()

    df_videos = get_youtube_radar(selected_skills=target_skills, limit=12)

    if not df_videos.empty:
        # Render responsive 3-column video cards
        cols = st.columns(3)
        for idx, row in df_videos.iterrows():
            col = cols[idx % 3]
            views_fmt = f"{humanize_number(row['view_count'])} views"
            thumb = row["thumbnail_url"] or f"https://i.ytimg.com/vi/{row['video_id']}/hqdefault.jpg"

            card_html = f"""
            <div class="yt-card">
                <div class="yt-thumb-wrap">
                    <img src="{thumb}" class="yt-thumb" alt="{row['skill_name']} tutorial thumbnail" loading="lazy" />
                    <span class="yt-skill-pill">{row['skill_name']}</span>
                </div>
                <div class="yt-body">
                    <div class="yt-title" title="{row['video_title']}">{row['video_title']}</div>
                    <div class="yt-meta">
                        <span>{row['channel_name']}</span>
                        <span>{views_fmt}</span>
                    </div>
                    <a href="{row['video_url']}" target="_blank" class="yt-btn">
                        <span>Tonton di YouTube</span>
                    </a>
                </div>
            </div>
            """
            with col:
                st.markdown(card_html, unsafe_allow_html=True)
                st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    else:
        st.info("Belum ada video YouTube yang terpetakan untuk skill ini.")


# === TAB 3: JOB EXPLORER & SALARY RADAR ===
with tab_explorer:
    st.markdown("### Eksplorasi Lowongan Kerja & Kompensasi")

    # Salary benchmarks overview
    df_sal = get_salary_insights()
    if not df_sal.empty:
        st.markdown("#### Tolok Ukur Gaji Berdasarkan Kategori Posisi (Juta IDR / Bulan)")
        fig_sal = go.Figure()
        fig_sal.add_trace(
            go.Bar(
                name="Gaji Minimum",
                x=df_sal["role_category"],
                y=df_sal["min_sal_jt"],
                marker_color="#6366F1",
            )
        )
        fig_sal.add_trace(
            go.Bar(
                name="Rata-rata",
                x=df_sal["role_category"],
                y=df_sal["avg_sal_jt"],
                marker_color="#06B6D4",
            )
        )
        fig_sal.add_trace(
            go.Bar(
                name="Gaji Maksimum",
                x=df_sal["role_category"],
                y=df_sal["max_sal_jt"],
                marker_color="#10B981",
            )
        )
        fig_sal.update_layout(barmode="group")
        apply_dark_chart_theme(fig_sal, height=300)
        st.plotly_chart(fig_sal, width="stretch")

    # In-Page Search & Filter Controls (Instant Access on Mobile & Desktop)
    st.markdown("#### Filter & Pencarian Langsung")
    col_search, col_f_type, col_f_role, col_f_policy = st.columns([2.5, 1.2, 1.3, 1.2])
    with col_search:
        inline_search = st.text_input(
            "Cari Posisi, Skill, atau Perusahaan",
            value=search_keyword if search_keyword else "",
            placeholder="Ketik kata kunci: intern, magang, backend, data, insignia...",
            key="inline_search_kw",
        )
    with col_f_type:
        active_type_idx = type_options.index(selected_type) if selected_type in type_options else 0
        inline_type = st.selectbox(
            "Tipe Pekerjaan",
            options=type_options,
            index=active_type_idx,
            key="inline_type_select",
        )
    with col_f_role:
        active_role_idx = role_options.index(selected_role) if selected_role in role_options else 0
        inline_role = st.selectbox(
            "Kategori Posisi",
            options=role_options,
            index=active_role_idx,
            key="inline_role_select",
        )
    with col_f_policy:
        active_policy_idx = policy_options.index(selected_policy) if selected_policy in policy_options else 0
        inline_policy = st.selectbox(
            "Kebijakan Kerja",
            options=policy_options,
            index=active_policy_idx,
            key="inline_policy_select",
        )

    # Active filters (inline input takes effect immediately)
    effective_role = inline_role if inline_role != "All Roles" else selected_role
    effective_policy = inline_policy if inline_policy != "All Policies" else selected_policy
    effective_type = inline_type if inline_type != "All Types" else selected_type
    effective_kw = inline_search.strip() if inline_search.strip() else search_keyword

    # Filtered Jobs Table
    df_jobs = get_jobs_explorer(
        role=effective_role,
        work_policy=effective_policy,
        skill=selected_skill,
        search_keyword=effective_kw,
        employment_type=effective_type,
        limit=100,
    )

    st.markdown(f"#### Daftar Lowongan Kerja ({len(df_jobs)} Posisi Ditemukan)")
    if not df_jobs.empty:
        # Display clean styled dataframe
        display_df = df_jobs[
            [
                "job_title",
                "company_name",
                "employment_type",
                "role_category",
                "work_policy",
                "salary_display",
                "company_location",
                "source_portal",
                "job_url",
            ]
        ].copy()

        display_df.columns = [
            "Posisi",
            "Perusahaan",
            "Tipe Kerja",
            "Kategori",
            "Kebijakan Kerja",
            "Estimasi Gaji",
            "Lokasi",
            "Portal",
            "Tautan Lamaran",
        ]

        st.dataframe(
            display_df,
            width="stretch",
            column_config={
                "Tautan Lamaran": st.column_config.LinkColumn(
                    "Tautan Lamaran",
                    display_text="Lamar Pekerjaan",
                ),
            },
            hide_index=True,
        )
    else:
        st.info("Tidak ada lowongan kerja yang cocok dengan kombinasi filter saat ini.")


# === TAB 4: ARCHITECTURE & METADATA ===
with tab_arch:
    st.markdown("### Arsitektur Medallion Serverless ($0 Cloud Compute)")

    st.markdown(
        """
        Platform ini dibangun menggunakan filosofi **Ponytail** (lean, zero-overengineering, zero-burn cost)
        dengan pola Medallion Lakehouse yang dijalankan secara otomatis di **GitHub Actions Free Tier**:
        """
    )

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.markdown(
            """
            <div class="kpi-card">
                <div style="font-size: 13px; font-weight: 700; color: #F59E0B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Bronze Layer</div>
                <div style="font-size: 12px; color: #CBD5E1; line-height: 1.6;">
                    <b>Format:</b> Raw Parquet (Snappy)<br/>
                    <b>Partisi:</b> <code>source=.../dt=...</code><br/>
                    <b>Scraper:</b> <code>curl_cffi</code> Chrome 120 impersonation + circuit breaker.<br/>
                    <b>YouTube:</b> 21-day TTL cache guard (0 API quota burn).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_m2:
        st.markdown(
            """
            <div class="kpi-card">
                <div style="font-size: 13px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Silver Layer</div>
                <div style="font-size: 12px; color: #CBD5E1; line-height: 1.6;">
                    <b>Engine:</b> PySpark Delta Lake (4GB driver)<br/>
                    <b>Cleansing:</b> Role categorization & IDR normalization.<br/>
                    <b>Skill Extractor:</b> Strict word-boundary regex (39 catalog skills).<br/>
                    <b>ACID:</b> Delta <code>MERGE INTO</code> deduplication.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_m3:
        st.markdown(
            """
            <div class="kpi-card">
                <div style="font-size: 13px; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Gold Layer</div>
                <div style="font-size: 12px; color: #CBD5E1; line-height: 1.6;">
                    <b>Engine:</b> dbt-core + dbt-duckdb<br/>
                    <b>Schema:</b> Kimball Star Schema (Fact + Dims).<br/>
                    <b>SCD 2:</b> <code>scd_dim_companies</code> change tracking.<br/>
                    <b>Storage:</b> Local DuckDB + Azure ADLS Gen2 sync.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Kimball Gold Models Summary")

    st.markdown(
        """
        | Model | Tipe | Deskripsi | Grain |
        |---|---|---|---|
        | `fact_job_postings` | Fact Table | Transaksi lowongan kerja aktif | 1 baris per lowongan pekerjaan |
        | `dim_companies` | Dimension (SCD2) | Profil perusahaan dan riwayat remote policy | 1 baris per versi perusahaan |
        | `dim_skills` | Dimension | Master keahlian teknis (39 skills) | 1 baris per teknologi |
        | `bridge_job_skills` | Bridge Table | Relasi M:N fakta lowongan dengan dimensi skill | 1 baris per pasangan job & skill |
        | `dim_youtube_videos` | Dimension | Metadata video pembelajaran YouTube | 1 baris per video tutorial |
        """
    )
