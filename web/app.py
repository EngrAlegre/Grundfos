import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
import re
import time
from src.agent import lookup_pump
from src.pump_dictionary import get_from_db  # Added import for local DB lookup

st.set_page_config(
    page_title="NeuralFlow - Pump Researcher",
    page_icon="🔍",
    layout="centered",
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 1.1rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .result-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f2937;
    }
    .unknown-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #9ca3af;
    }
    .search-hint {
        text-align: center;
        color: #9ca3af;
        font-size: 0.9rem;
        margin-top: 10px;
    }
    /* Badge Styles */
    .source-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 10px;
        color: white;
    }
    .source-local {
        background-color: #10b981; /* Green for fast/local */
    }
    .source-web {
        background-color: #3b82f6; /* Blue for web */
    }
    div[data-testid="stForm"] {
        border: 2px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">NeuralFlow</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-Powered Pump Specification Researcher</div>', unsafe_allow_html=True)


def parse_natural_query(query: str) -> tuple[str, str]:
    query = query.strip()

    known_brands = [
        "TACO", "WILO", "BIRAL", "EMB", "SMEDEGAARD",
        "DAB", "CIRCAL", "LOEWE", "GRUNDFOS", "XYLEM",
    ]

    prefixes = [
        r"(?:give\s+me\s+)?(?:the\s+)?(?:specifications?|specs?|data|info)\s+(?:for|of|on)\s+(?:a\s+)?",
        r"(?:look\s*up|search|find|get)\s+",
        r"(?:what\s+(?:are|is)\s+the\s+(?:specs?|specifications?|data)\s+(?:for|of)\s+)",
    ]
    for p in prefixes:
        query = re.sub(p, "", query, flags=re.IGNORECASE).strip()

    for brand in known_brands:
        pattern = rf"^{re.escape(brand)}\b\s*(.+)"
        m = re.match(pattern, query, re.IGNORECASE)
        if m:
            return brand.upper(), m.group(1).strip()

    parts = query.split(None, 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1].strip()
    return "", query


# Helper to display a single result column (Web or Local)
def render_single_result(title, result, manufacturer, prodname, elapsed=None, source_type="web"):
    st.markdown(f"#### {title}")
    
    # Using the same CSS classes for consistency
    col1, col2, col3 = st.columns(3)
    flow = result.get("FLOWNOM56", "unknown")
    head = result.get("HEADNOM56", "unknown")
    phase = result.get("PHASE", "unknown")

    with col1:
        cls = "unknown-value" if flow == "unknown" else "metric-value"
        display = "N/A" if flow == "unknown" else f"{flow}"
        unit = "" if flow == "unknown" else " m3/h"
        st.markdown(f'<div class="metric-label">Flow Rate</div><div class="{cls}">{display}<span style="font-size:0.9rem;font-weight:400">{unit}</span></div>', unsafe_allow_html=True)

    with col2:
        cls = "unknown-value" if head == "unknown" else "metric-value"
        display = "N/A" if head == "unknown" else f"{head}"
        unit = "" if head == "unknown" else " m"
        st.markdown(f'<div class="metric-label">Head</div><div class="{cls}">{display}<span style="font-size:0.9rem;font-weight:400">{unit}</span></div>', unsafe_allow_html=True)

    with col3:
        cls = "unknown-value" if phase == "unknown" else "metric-value"
        display = "N/A" if phase == "unknown" else f"{phase}-Phase"
        st.markdown(f'<div class="metric-label">Electrical Phase</div><div class="{cls}">{display}</div>', unsafe_allow_html=True)

    # Badge and Time
    badge_class = "source-web" if source_type == "web" else "source-local"
    badge_text = "Web Search" if source_type == "web" else "Local DB"
    time_str = f"| {elapsed:.1f}s" if elapsed else ""
    
    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:center; margin-top:10px;">'
        f'<span class="source-badge {badge_class}">{badge_text}</span>'
        f'<span style="margin-left:10px; color:#9ca3af; font-size:0.9rem;">{time_str}</span>'
        f'</div>', 
        unsafe_allow_html=True
    )

    with st.expander("Raw JSON"):
        output = {
            "MANUFACTURER": manufacturer,
            "PRODNAME": prodname,
            "FLOWNOM56": flow,
            "HEADNOM56": head,
            "PHASE": phase,
        }
        st.json(output)


tab1, tab2 = st.tabs(["Natural Search", "Manual Input"])

with tab1:
    with st.form("natural_form"):
        query = st.text_input(
            "Ask about any pump",
            placeholder="e.g. Give me the specifications for a TACO 0014-SF1",
        )
        submitted = st.form_submit_button("Search", use_container_width=True)

    if submitted and query:
        manufacturer, prodname = parse_natural_query(query)
        if not manufacturer:
            st.warning("Could not detect the manufacturer. Try: `TACO 0014-SF1`")
        else:
            # IMPORTANT: Fetch Local Data FIRST to avoid the Web search overwriting it before display
            local_result = get_from_db(manufacturer, prodname)
            
            # 2. Fetch Web Data (Force web search)
            with st.spinner(f"Searching web for {manufacturer} {prodname}..."):
                start = time.time()
                web_result = lookup_pump(manufacturer, prodname, force_web=True)
                web_elapsed = time.time() - start

            # 3. Display in 2 Columns
            col_web, col_db = st.columns(2)
            
            with col_web:
                render_single_result("🌐 Web Search Result", web_result, manufacturer, prodname, web_elapsed, "web")
            
            with col_db:
                if local_result:
                    render_single_result("💾 Local Database", local_result, manufacturer, prodname, None, "local")
                else:
                    st.markdown("#### 💾 Local Database")
                    st.info("No data found in local database.")

with tab2:
    with st.form("manual_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            mfr = st.selectbox(
                "Manufacturer",
                ["TACO", "WILO", "BIRAL (BIERI, HOVAL)", "EMB", "SMEDEGAARD", "DAB / CIRCAL", "LOEWE"],
            )
        with col_b:
            prod = st.text_input("Product Name", placeholder="e.g. 0014-SF1")
        manual_submit = st.form_submit_button("Look Up", use_container_width=True)

    if manual_submit and prod:
        # IMPORTANT: Fetch Local Data FIRST
        local_result = get_from_db(mfr, prod)
        
        # 2. Fetch Web Data (Force web search)
        with st.spinner(f"Searching web for {mfr} {prod}..."):
            start = time.time()
            web_result = lookup_pump(mfr, prod, force_web=True)
            web_elapsed = time.time() - start

        # 3. Display in 2 Columns
        col_web, col_db = st.columns(2)
        
        with col_web:
            render_single_result("🌐 Web Search Result", web_result, mfr, prod, web_elapsed, "web")
        
        with col_db:
            if local_result:
                render_single_result("💾 Local Database", local_result, mfr, prod, None, "local")
            else:
                st.markdown("#### 💾 Local Database")
                st.info("No data found in local database.")

st.markdown("---")
st.markdown('<div class="search-hint">Powered by SerpAPI + Mistral 7B | Results cached for faster repeat lookups</div>', unsafe_allow_html=True)