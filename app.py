"""
Devtacet Lead Intelligence Dashboard
Spatial UI — native Streamlit patterns, no custom CSS
"""

import glob
import subprocess
import sys
import time
import traceback

import pandas as pd
import streamlit as st
import plotly.express as px


# ─── Playwright browser bootstrap ─────────────────────────────────────────────
# Streamlit Cloud has no Chromium binary pre-installed.
# This ensures chromium and chromium-headless-shell are installed in the cloud container.

@st.cache_resource(show_spinner=False)
def ensure_playwright_browsers() -> None:
    """Ensure Playwright Chromium is installed."""
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        st.warning(f"Note: Playwright browser check: {e}")

ensure_playwright_browsers()


st.set_page_config(
    page_title="Devtacet Lead Pipeline",
    page_icon=":material/target:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Helpers ────────────────────────────────────────────────────────────────

SERVICE_COLORS = {
    "Website/SEO":     "blue",
    "Website Redesign":"violet",
    "Android App":     "green",
    "SEO":             "orange",
    "System Software": "red",
    "Low priority":    "gray",
}

def _badge(service: str) -> str:
    color = SERVICE_COLORS.get(service, "gray")
    return f":{color}-badge[{service}]"


def generate_pitch(lead: pd.Series) -> str:
    name    = lead.get("name", "Business Owner")
    service = lead.get("recommended_service", "Digital Services")

    lines = [f"Hi {name} Team,\n"]
    lines.append("I came across your Google Maps listing and noticed a few opportunities to help you win more customers online.\n")

    hw  = str(lead.get("has_website", "false")).lower() == "true"
    sr  = str(lead.get("site_reachable", "false")).lower() == "true"
    mf  = str(lead.get("mobile_friendly", "false")).lower() == "true"

    if not hw:
        lines.append(
            "You don't have a website linked to your Maps profile. A fast, "
            "well-structured website converts local searchers into paying customers — "
            "we can have one live in under two weeks."
        )
    elif not sr:
        lines.append(
            "Your website appears to be currently down, which means you're losing "
            "inbound traffic right now. We can restore and harden your hosting to "
            "guarantee 99.9% uptime."
        )
    elif not mf:
        lines.append(
            "Your site isn't mobile-friendly (no responsive viewport). Over 75% of "
            "local searches happen on phones — a mobile-first redesign would immediately "
            "improve conversions."
        )
    elif service == "Android App":
        lines.append(
            "Your category is ideal for a branded mobile app or automated booking system. "
            "We build lightweight Android apps that cut third-party fees and drive repeat business."
        )
    elif service == "SEO":
        lines.append(
            "Your site is missing schema markup and meta optimisation, limiting how high "
            "you appear on Google. Our SEO package handles the full technical upgrade."
        )
    else:
        lines.append(
            "We help businesses upgrade their digital presence and internal tooling — "
            "websites, SEO, apps, and custom software built for your niche."
        )

    lines.append("\nWould you be open to a free 10-minute audit call this week?\n\nBest,\nDevtacet Team")
    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def load_dataset(path_or_file) -> pd.DataFrame:
    try:
        df = pd.read_csv(path_or_file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return pd.DataFrame()

    bool_cols = ["has_website", "site_reachable", "mobile_friendly",
                 "is_https", "has_meta_description", "has_schema_markup"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.strip().str.lower()
                .map({"true": True, "false": False})
                .fillna(False)
            )

    for col, dtype in [("lead_score", int), ("review_count", int)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(dtype)

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0)

    if "score_reasons" in df.columns:
        df["score_reasons"] = df["score_reasons"].fillna("")

    return df


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Devtacet", anchor=False)
    st.caption("Lead Intelligence Pipeline")

    available_files = sorted(glob.glob("*.csv"))

    data_mode = st.segmented_control(
        "Data source",
        options=["CSV file", "Upload", "Scraper"],
        default="CSV file",
        label_visibility="collapsed",
    )

    df_raw = pd.DataFrame()

    if data_mode == "CSV file":
        if available_files:
            chosen = st.selectbox(
                "Select file",
                available_files,
                label_visibility="collapsed",
            )
            df_raw = load_dataset(chosen)
        else:
            st.caption("No CSV files found. Run a scrape or upload one.")

    elif data_mode == "Upload":
        uploaded = st.file_uploader(
            "Upload leads CSV",
            type=["csv"],
            label_visibility="collapsed",
        )
        if uploaded:
            df_raw = load_dataset(uploaded)

    else:
        st.caption("Configure your search in the :material/rocket_launch: Scraper tab.")

    # ── Filters (only shown when data is loaded) ──────────────────────────
    if not df_raw.empty:
        st.markdown("**Filters**")

        search_q = st.text_input(
            "Search",
            placeholder="Name, address, category, phone…",
            label_visibility="collapsed",
        )

        all_services = sorted(df_raw["recommended_service"].dropna().unique().tolist()) if "recommended_service" in df_raw.columns else []
        sel_services = st.pills(
            "Service",
            options=all_services,
            selection_mode="multi",
            default=all_services,
        )

        all_cats = sorted(df_raw["category"].dropna().unique().tolist()) if "category" in df_raw.columns else []
        sel_cats = st.multiselect("Category", all_cats, default=all_cats, label_visibility="visible")

        min_s = int(df_raw["lead_score"].min()) if "lead_score" in df_raw.columns else 0
        max_s = int(df_raw["lead_score"].max()) if "lead_score" in df_raw.columns else 100
        if min_s == max_s:
            max_s += 10
        score_range = st.slider("Score range", min_s, max_s, (min_s, max_s))

        with st.expander(":material/tune: Website audit filters", expanded=False):
            f_website   = st.selectbox("Has website",      ["All", "Yes", "No"])
            f_reachable = st.selectbox("Site reachable",   ["All", "Reachable", "Down"])
            f_mobile    = st.selectbox("Mobile friendly",  ["All", "Yes", "No"])
            f_https     = st.selectbox("HTTPS secure",     ["All", "Yes", "No"])
            f_schema    = st.selectbox("Schema markup",    ["All", "Present", "Missing"])

        with st.expander(":material/star: Rating & reviews", expanded=False):
            min_rating  = st.slider("Min rating",  0.0, 5.0, 0.0, 0.1)
            min_reviews = st.number_input("Min reviews", min_value=0, value=0, step=5)

    else:
        search_q = ""
        sel_services = []
        sel_cats = []
        score_range = (0, 100)
        f_website = f_reachable = f_mobile = f_https = f_schema = "All"
        min_rating = 0.0
        min_reviews = 0


# ─── Apply Filters ───────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if search_q:
        q = search_q.lower()
        text_cols = ["name", "address", "category", "phone", "score_reasons"]
        mask = pd.Series(False, index=out.index)
        for c in text_cols:
            if c in out.columns:
                mask |= out[c].astype(str).str.lower().str.contains(q, na=False)
        out = out[mask]

    if sel_services and "recommended_service" in out.columns:
        out = out[out["recommended_service"].isin(sel_services)]

    if sel_cats and "category" in out.columns:
        out = out[out["category"].isin(sel_cats)]

    if "lead_score" in out.columns:
        out = out[(out["lead_score"] >= score_range[0]) & (out["lead_score"] <= score_range[1])]

    if "rating" in out.columns:
        out = out[out["rating"] >= min_rating]

    if "review_count" in out.columns:
        out = out[out["review_count"] >= min_reviews]

    bool_map = {
        ("has_website",    "Yes"):      lambda d: d[d["has_website"] == True],
        ("has_website",    "No"):       lambda d: d[d["has_website"] == False],
        ("site_reachable", "Reachable"):lambda d: d[d["site_reachable"] == True],
        ("site_reachable", "Down"):     lambda d: d[(d["has_website"] == True) & (d["site_reachable"] == False)],
        ("mobile_friendly","Yes"):      lambda d: d[d["mobile_friendly"] == True],
        ("mobile_friendly","No"):       lambda d: d[(d["has_website"] == True) & (d["mobile_friendly"] == False)],
        ("is_https",       "Yes"):      lambda d: d[d["is_https"] == True],
        ("is_https",       "No"):       lambda d: d[(d["has_website"] == True) & (d["is_https"] == False)],
        ("has_schema_markup","Present"):lambda d: d[d["has_schema_markup"] == True],
        ("has_schema_markup","Missing"):lambda d: d[(d["has_website"] == True) & (d["has_schema_markup"] == False)],
    }
    for (col, val), fn in bool_map.items():
        fval = locals().get(f"f_{col.split('_')[0]}", "All") if col != "has_schema_markup" else f_schema
        # resolve the right filter variable
    # Apply each filter directly
    for (col, val), fn in bool_map.items():
        filter_val = {
            "has_website":     f_website,
            "site_reachable":  f_reachable,
            "mobile_friendly": f_mobile,
            "is_https":        f_https,
            "has_schema_markup": f_schema,
        }.get(col, "All")
        if filter_val == val and col in out.columns:
            out = fn(out)

    return out


filtered_df = apply_filters(df_raw) if not df_raw.empty else pd.DataFrame()


# ─── Main area ───────────────────────────────────────────────────────────────

st.title("Lead Intelligence", anchor=False, icon=":material/target:")

tab_explore, tab_analytics, tab_scraper, tab_export = st.tabs([
    ":material/manage_search: Explorer",
    ":material/bar_chart: Analytics",
    ":material/rocket_launch: Scraper",
    ":material/download: Export",
])


# ── TAB: SCRAPER ─────────────────────────────────────────────────────────────

with tab_scraper:
    st.subheader("Live Google Maps scraper", anchor=False, icon=":material/rocket_launch:")
    st.caption("Run the full pipeline — scrape → audit → score → save — without leaving the dashboard.")

    with st.form("scraper_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            niche_input  = st.text_input("Business niches (comma-separated)", value="dentists, restaurants, gyms")
            city_input   = st.text_input("Target city", value="Lucknow")
            max_results  = st.number_input("Max results per niche", 1, 100, 10, 5)
        with col_b:
            out_filename = st.text_input("Output CSV filename", value="leads.csv")
            show_browser = st.checkbox("Show browser window (debug)")
            delay_sec    = st.slider("Delay between audits (s)", 0.5, 3.0, 1.0, 0.5)

        launched = st.form_submit_button(
            "Launch pipeline",
            type="primary",
            icon=":material/play_arrow:",
        )

    if launched:
        niches_list = [n.strip() for n in niche_input.split(",") if n.strip()]
        if not niches_list or not city_input.strip():
            st.error("Provide at least one niche and a city.", icon=":material/error:")
        else:
            try:
                from gmaps_scraper import GoogleMapsScraper
                from enrich import analyze_website
                from scorer import score_lead
                from main import dedupe, write_csv

                t0 = time.time()

                # ── Phase 1: scraping ─────────────────────────────────────
                with st.status("Scraping Google Maps…", expanded=True) as scrape_status:
                    scraper = GoogleMapsScraper(headless=not show_browser)
                    all_businesses = []
                    try:
                        for i, niche in enumerate(niches_list, 1):
                            query = f"{niche} in {city_input.strip()}"
                            st.write(f":material/search: `{query}` ({i}/{len(niches_list)})")
                            results = scraper.search(query, max_results=int(max_results))
                            all_businesses.extend(results)
                            st.write(f":material/check_circle: **{len(results)}** listings found — running total: **{len(all_businesses)}**")
                    finally:
                        scraper.close()

                    all_businesses = dedupe(all_businesses)
                    st.write(f":material/filter_list: After deduplication: **{len(all_businesses)}** unique leads")
                    scrape_status.update(
                        label=f"Scraping complete — {len(all_businesses)} unique leads",
                        state="complete",
                    )

                # ── Phase 2: enrichment & scoring ────────────────────────
                total = len(all_businesses)
                prog  = st.progress(0, text="Auditing websites…")

                with st.status("Auditing websites & scoring…", expanded=True) as enrich_status:
                    enriched_rows = []
                    for j, biz in enumerate(all_businesses, 1):
                        website  = biz.get("website")
                        biz_name = biz.get("name", "Unknown")
                        st.write(
                            f":material/language: **{j}/{total}** `{biz_name}` → "
                            f"{website or '*no website*'}"
                        )

                        web    = analyze_website(website)
                        scored = score_lead(biz, web)

                        enriched_rows.append({
                            **biz,
                            "has_website":        web["has_website"],
                            "site_reachable":     web["reachable"],
                            "mobile_friendly":    web["mobile_friendly"],
                            "is_https":           web["is_https"],
                            "has_meta_description": web["has_meta_description"],
                            "has_schema_markup":  web["has_schema_markup"],
                            "recommended_service":scored["recommended_service"],
                            "lead_score":         scored["total_score"],
                            "score_reasons":      scored["reasons"],
                        })

                        prog.progress(
                            j / total,
                            text=f"Audited {j}/{total} — **{biz_name}** → score {scored['total_score']} pts",
                        )
                        st.write(
                            f"  :material/done: Score **{scored['total_score']} pts** "
                            f"({scored['recommended_service']})"
                        )

                        if website:
                            time.sleep(float(delay_sec))

                    enriched_rows.sort(key=lambda r: r["lead_score"], reverse=True)
                    write_csv(enriched_rows, out_filename)
                    enrich_status.update(
                        label=f"Audit complete — {len(enriched_rows)} leads scored & saved",
                        state="complete",
                    )

                elapsed = round(time.time() - t0, 1)
                st.success(
                    f"Pipeline finished in **{elapsed}s**. "
                    f"**{len(enriched_rows)}** leads saved to `{out_filename}`. "
                    f"Select it from the sidebar to explore results.",
                    icon=":material/celebration:",
                )
                load_dataset.clear()

            except Exception as err:
                st.error(f"Pipeline error: {err}", icon=":material/error:")
                st.code(traceback.format_exc())


# ── TAB: EXPLORER ────────────────────────────────────────────────────────────

with tab_explore:
    if df_raw.empty:
        st.info(
            "No data loaded. Select a CSV from the sidebar or run the scraper.",
            icon=":material/info:",
        )
    else:
        total_leads = len(df_raw)
        fc          = len(filtered_df)
        hot         = len(filtered_df[filtered_df["lead_score"] >= 35]) if "lead_score" in filtered_df.columns else 0
        no_web      = len(filtered_df[filtered_df["has_website"] == False]) if "has_website" in filtered_df.columns else 0
        avg_score   = round(filtered_df["lead_score"].mean(), 1) if not filtered_df.empty and "lead_score" in filtered_df.columns else 0.0
        top_svc     = (
            filtered_df["recommended_service"].mode()[0]
            if not filtered_df.empty and "recommended_service" in filtered_df.columns
            else "N/A"
        )

        # KPI row — native horizontal container with bordered metrics
        with st.container(horizontal=True):
            st.metric("Leads shown", f"{fc} / {total_leads}", border=True)
            st.metric("Hot leads (≥35 pts)", hot, border=True)
            st.metric("Missing website", no_web, border=True)
            st.metric("Avg score", avg_score, border=True)
            st.metric("Top pitch line", top_svc, border=True)

        st.space("small")

        col_ctrl1, col_ctrl2 = st.columns([3, 1])
        with col_ctrl1:
            view_mode = st.segmented_control(
                "Layout",
                options=["Cards", "Table"],
                default="Cards",
                label_visibility="collapsed",
            )
        with col_ctrl2:
            sort_by = st.selectbox(
                "Sort",
                ["Score ↓", "Score ↑", "Rating ↓", "Name A–Z"],
                label_visibility="collapsed",
            )

        sort_map = {
            "Score ↓": ("lead_score", False),
            "Score ↑": ("lead_score", True),
            "Rating ↓": ("rating", False),
            "Name A–Z": ("name", True),
        }
        scol, sasc = sort_map[sort_by]
        if scol in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by=scol, ascending=sasc)

        if filtered_df.empty:
            st.warning("No leads match the current filters.", icon=":material/filter_list_off:")

        elif view_mode == "Table":
            display_cols = [
                "name", "category", "recommended_service", "lead_score",
                "rating", "review_count", "phone",
                "has_website", "mobile_friendly", "is_https", "has_schema_markup",
                "score_reasons",
            ]
            show_cols = [c for c in display_cols if c in filtered_df.columns]
            st.dataframe(
                filtered_df[show_cols],
                hide_index=True,
                column_config={
                    "name":               st.column_config.TextColumn("Business", width="medium"),
                    "recommended_service":st.column_config.TextColumn("Target service"),
                    "lead_score":         st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d pts"),
                    "rating":             st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                    "has_website":        st.column_config.CheckboxColumn("Website"),
                    "mobile_friendly":    st.column_config.CheckboxColumn("Mobile"),
                    "is_https":           st.column_config.CheckboxColumn("HTTPS"),
                    "has_schema_markup":  st.column_config.CheckboxColumn("Schema"),
                },
            )

        else:
            # Cards view
            for idx, row in filtered_df.iterrows():
                score      = row.get("lead_score", 0)
                rec_svc    = row.get("recommended_service", "General")
                hw         = row.get("has_website", False)
                sr         = row.get("site_reachable", False)
                mf         = row.get("mobile_friendly", False)
                is_https   = row.get("is_https", False)
                schema     = row.get("has_schema_markup", False)
                reasons    = row.get("score_reasons", "")

                # Score badge color
                if score >= 40:
                    score_badge = f":red-badge[{score} pts]"
                elif score >= 20:
                    score_badge = f":orange-badge[{score} pts]"
                else:
                    score_badge = f":green-badge[{score} pts]"

                with st.container(border=True):
                    hdr_col, badge_col = st.columns([5, 2])
                    with hdr_col:
                        st.markdown(f"### {row.get('name', 'Unknown')}")
                        st.caption(
                            f":material/location_on: {row.get('address', '—')} &nbsp;·&nbsp; "
                            f":material/label: **{row.get('category', 'Uncategorized')}** &nbsp;·&nbsp; "
                            f":material/star: {row.get('rating', 0.0)} ({row.get('review_count', 0)} reviews)"
                        )
                    with badge_col:
                        st.markdown(f"{_badge(rec_svc)} {score_badge}", unsafe_allow_html=False)

                    audit_col, links_col = st.columns([3, 1])
                    with audit_col:
                        # Audit badges using native st.badge
                        with st.container(horizontal=True):
                            if hw:
                                st.badge("Website", icon=":material/language:", color="green")
                            else:
                                st.badge("No website", icon=":material/language:", color="red")

                            if hw:
                                st.badge(
                                    "Reachable" if sr else "Unreachable",
                                    icon=":material/check_circle:" if sr else ":material/error:",
                                    color="green" if sr else "red",
                                )
                                st.badge(
                                    "Mobile-ready" if mf else "Not mobile",
                                    icon=":material/smartphone:",
                                    color="green" if mf else "orange",
                                )
                                st.badge(
                                    "HTTPS" if is_https else "HTTP only",
                                    icon=":material/lock:" if is_https else ":material/lock_open:",
                                    color="green" if is_https else "orange",
                                )
                                st.badge(
                                    "Schema" if schema else "No schema",
                                    icon=":material/data_object:",
                                    color="green" if schema else "orange",
                                )

                        if reasons:
                            st.caption(f":material/report: {reasons}")

                    with links_col:
                        if row.get("website"):
                            st.link_button(
                                "Visit website",
                                url=row["website"],
                                icon=":material/open_in_new:",
                            )
                        if row.get("maps_url"):
                            st.link_button(
                                "Google Maps",
                                url=row["maps_url"],
                                icon=":material/map:",
                            )
                        if row.get("phone"):
                            st.caption(f":material/call: `{row['phone']}`")

                    with st.expander(
                        f"Generate outreach pitch for {row.get('name')}",
                        icon=":material/mail:",
                    ):
                        pitch = generate_pitch(row)
                        st.text_area(
                            "Outreach message",
                            value=pitch,
                            height=200,
                            key=f"pitch_{idx}",
                            label_visibility="collapsed",
                        )
                        st.caption("Copy and send via email, WhatsApp, or LinkedIn DM.")


# ── TAB: ANALYTICS ──────────────────────────────────────────────────────────

with tab_analytics:
    if filtered_df.empty:
        st.info("Load data to view analytics.", icon=":material/info:")
    else:
        st.subheader("Opportunity breakdown", anchor=False, icon=":material/bar_chart:")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            with st.container(border=True):
                st.markdown("**Recommended service distribution**")
                if "recommended_service" in filtered_df.columns:
                    svc_counts = filtered_df["recommended_service"].value_counts().reset_index()
                    svc_counts.columns = ["Service", "Count"]
                    fig = px.pie(
                        svc_counts,
                        values="Count",
                        names="Service",
                        hole=0.50,
                        color_discrete_sequence=["#6366f1","#8b5cf6","#14b8a6","#f59e0b","#ef4444","#71717a"],
                    )
                    fig.update_traces(textposition="inside", textinfo="percent+label")
                    fig.update_layout(margin=dict(t=20,b=10,l=10,r=10), showlegend=False,
                                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig)

        with col_g2:
            with st.container(border=True):
                st.markdown("**Lead opportunity score distribution**")
                if "lead_score" in filtered_df.columns:
                    fig2 = px.histogram(
                        filtered_df, x="lead_score", nbins=12,
                        labels={"lead_score": "Score (pts)"},
                        color_discrete_sequence=["#6366f1"],
                    )
                    fig2.update_layout(bargap=0.08, margin=dict(t=10,b=10,l=10,r=10),
                                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig2)

        col_g3, col_g4 = st.columns(2)

        with col_g3:
            with st.container(border=True):
                st.markdown("**Digital gaps detected**")
                gaps = {
                    "No website":       int((filtered_df["has_website"] == False).sum()),
                    "Not mobile":       int(((filtered_df["has_website"] == True) & (filtered_df["mobile_friendly"] == False)).sum()),
                    "HTTP only":        int(((filtered_df["has_website"] == True) & (filtered_df["is_https"] == False)).sum()),
                    "No schema":        int(((filtered_df["has_website"] == True) & (filtered_df["has_schema_markup"] == False)).sum()),
                }
                gap_df = pd.DataFrame(list(gaps.items()), columns=["Gap", "Count"])
                fig3 = px.bar(
                    gap_df, x="Gap", y="Count", color="Count",
                    color_continuous_scale=["#27272a","#ef4444"],
                )
                fig3.update_layout(
                    margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig3)

        with col_g4:
            with st.container(border=True):
                st.markdown("**Top business niches**")
                if "category" in filtered_df.columns:
                    cat_counts = filtered_df["category"].value_counts().head(8).reset_index()
                    cat_counts.columns = ["Category", "Count"]
                    fig4 = px.bar(
                        cat_counts, x="Count", y="Category", orientation="h",
                        color_discrete_sequence=["#8b5cf6"],
                    )
                    fig4.update_layout(
                        yaxis=dict(autorange="reversed"),
                        margin=dict(t=10,b=10,l=10,r=10),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig4)


# ── TAB: EXPORT ─────────────────────────────────────────────────────────────

with tab_export:
    if filtered_df.empty:
        st.info("Load data to export.", icon=":material/info:")
    else:
        st.subheader("Download filtered leads", anchor=False, icon=":material/download:")
        st.caption(f"{len(filtered_df)} leads match current filters.")

        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        fname = f"devtacet_leads_{time.strftime('%Y%m%d_%H%M%S')}.csv"

        st.download_button(
            label=f"Download {len(filtered_df)} leads as CSV",
            data=csv_bytes,
            file_name=fname,
            mime="text/csv",
            type="primary",
            icon=":material/download:",
        )

        st.space("small")
        with st.container(border=True):
            st.markdown("**Preview**")
            st.dataframe(filtered_df.head(10), hide_index=True)
