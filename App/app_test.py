from datetime import datetime
import json
from urllib import error, request

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(layout="wide", page_title="Global COVID Map")

BACKEND_DEFAULT_URL = "http://127.0.0.1:8000/api/v1/infections/snapshot"

ISO3_CODES = [
    "ABW", "AFG", "AGO", "AIA", "ALB", "AND", "ARE", "ARG", "ARM", "ASM", "ATG", "AUS", "AUT", "AZE",
    "BDI", "BEL", "BEN", "BES", "BFA", "BGD", "BGR", "BHR", "BHS", "BIH", "BLM", "BLR", "BLZ", "BMU",
    "BOL", "BRA", "BRB", "BRN", "BTN", "BWA", "CAF", "CAN", "CHE", "CHL", "CHN", "CIV", "CMR", "COD",
    "COG", "COK", "COL", "COM", "CPV", "CRI", "CUB", "CUW", "CYM", "CYP", "CZE", "DEU", "DJI", "DMA",
    "DNK", "DOM", "DZA", "ECU", "EGY", "ERI", "ESH", "ESP", "EST", "ETH", "FIN", "FJI", "FLK", "FRA",
    "FRO", "FSM", "GAB", "GBR", "GEO", "GGY", "GHA", "GIB", "GIN", "GLP", "GMB", "GNB", "GNQ", "GRC",
    "GRD", "GRL", "GTM", "GUF", "GUM", "GUY", "HKG", "HND", "HRV", "HTI", "HUN", "IDN", "IMN", "IND",
    "IRL", "IRN", "IRQ", "ISL", "ISR", "ITA", "JAM", "JEY", "JOR", "JPN", "KAZ", "KEN", "KGZ", "KHM",
    "KIR", "KNA", "KOR", "KWT", "LAO", "LBN", "LBR", "LBY", "LCA", "LIE", "LKA", "LSO", "LTU", "LUX",
    "LVA", "MAC", "MAF", "MAR", "MCO", "MDA", "MDG", "MDV", "MEX", "MHL", "MKD", "MLI", "MLT", "MMR",
    "MNE", "MNG", "MNP", "MOZ", "MRT", "MSR", "MTQ", "MUS", "MWI", "MYS", "MYT", "NAM", "NCL", "NER",
    "NGA", "NIC", "NIU", "NLD", "NOR", "NPL", "NRU", "NZL", "OMN", "PAK", "PAN", "PCN", "PER", "PHL",
    "PLW", "PNG", "POL", "PRI", "PRK", "PRT", "PRY", "PSE", "PYF", "QAT", "REU", "ROU", "RUS", "RWA",
    "SAU", "SDN", "SEN", "SGP", "SHN", "SLB", "SLE", "SLV", "SMR", "SOM", "SPM", "SRB", "SSD", "STP",
    "SUR", "SVK", "SVN", "SWE", "SWZ", "SXM", "SYC", "SYR", "TCA", "TCD", "TGO", "THA", "TJK", "TKL",
    "TKM", "TLS", "TON", "TTO", "TUN", "TUR", "TUV", "TWN", "TZA", "UGA", "UKR", "URY", "USA", "UZB",
    "VAT", "VCT", "VEN", "VGB", "VIR", "VNM", "VUT", "WLF", "WSM", "YEM", "ZAF", "ZMB", "ZWE",
]


def fetch_backend_snapshot(country_code: str, api_url: str) -> dict:
    """通过后端接口拿快照，后续可直接替换为正式接口。"""
    payload = json.dumps({"country_code": country_code}).encode("utf-8")
    req = request.Request(
        url=api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, ValueError) as exc:
        st.warning(f"Backend connection failed: {exc}")
        return {
            "time": datetime.now().strftime("%Y:%m:%d"),
            "infections_by_country": {},
        }

    if "time" not in data or "infections_by_country" not in data:
        st.warning("Backend response format is invalid.")
        return {
            "time": datetime.now().strftime("%Y:%m:%d"),
            "infections_by_country": {},
        }

    return data


def build_map_frame(snapshot: dict) -> pd.DataFrame:
    cases = snapshot.get("infections_by_country", {}) or {}
    rows = [{"code": code, "cases": float(cases.get(code, 0))} for code in ISO3_CODES]
    df = pd.DataFrame(rows)

    max_cases = float(df["cases"].max())
    if max_cases <= 0:
        max_cases = 1.0

    df["risk_level"] = pd.cut(
        df["cases"],
        bins=[-1, max_cases * 0.05, max_cases * 0.2, max_cases * 0.5, max_cases],
        labels=["Low", "Medium", "High", "Very High"],
    ).astype(str)
    return df


def create_map_figure(map_df: pd.DataFrame) -> go.Figure:
    z_max = max(float(map_df["cases"].max()), 1.0)

    fig = go.Figure(
        data=go.Choropleth(
            locations=map_df["code"],
            z=map_df["cases"],
            locationmode="ISO-3",
            customdata=map_df[["risk_level", "code"]],
            showscale=False,
            colorscale=[
                [0.00, "#ffd6d6"],
                [0.35, "#ff8f8f"],
                [0.70, "#ff3d3d"],
                [1.00, "#a60000"],
            ],
            zmin=0,
            zmax=z_max,
            marker_line_width=0.35,
            marker_line_color="#2d0b0b",
            hovertemplate="Country Code: %{location}<br>Risk Level: %{customdata[0]}<extra></extra>",
        )
    )

    fig.update_geos(
        scope="world",
        projection_type="natural earth",
        showcountries=True,
        countrycolor="#2d0b0b",
        showcoastlines=True,
        coastlinecolor="#141414",
        showocean=True,
        oceancolor="#050505",
        showlakes=True,
        lakecolor="#050505",
        showland=True,
        landcolor="#ffb3b3",
        bgcolor="#050505",
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=12, b=0),
        paper_bgcolor="#050505",
        plot_bgcolor="#050505",
        font=dict(color="#ffeaea"),
    )

    return fig


def extract_selected_code(plot_event) -> str | None:
    if plot_event is None:
        return None

    points = []
    selection = getattr(plot_event, "selection", None)
    if selection is not None:
        points = getattr(selection, "points", []) or []

    if not points and isinstance(plot_event, dict):
        points = plot_event.get("selection", {}).get("points", [])

    if not points:
        return None

    first_point = points[0]
    if isinstance(first_point, dict):
        location = first_point.get("location")
    else:
        location = getattr(first_point, "location", None)

    if not location:
        return None
    return str(location).upper()


st.title("🌍 Global Infection Heat Map")

with st.sidebar:
    st.header("Backend Connection")
    backend_url = st.text_input("Snapshot API URL", value=BACKEND_DEFAULT_URL)
    st.caption("Click a country on the map to send its ISO-3 code to backend.")

if "snapshot" not in st.session_state:
    st.session_state.snapshot = {
        "time": datetime.now().strftime("%Y:%m:%d"),
        "infections_by_country": {},
    }
if "selected_country_code" not in st.session_state:
    st.session_state.selected_country_code = "USA"
if "last_requested_code" not in st.session_state:
    st.session_state.last_requested_code = None

if st.session_state.last_requested_code is None:
    st.session_state.snapshot = fetch_backend_snapshot(
        st.session_state.selected_country_code,
        backend_url,
    )
    st.session_state.last_requested_code = st.session_state.selected_country_code

map_df = build_map_frame(st.session_state.snapshot)
fig = create_map_figure(map_df)

try:
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key="infection_world_map",
        on_select="rerun",
    )
except TypeError:
    st.warning("Your current Streamlit version does not support click selection on Plotly charts.")
    st.plotly_chart(fig, use_container_width=True, key="infection_world_map_fallback")
    event = None

clicked_code = extract_selected_code(event)
if clicked_code and clicked_code in ISO3_CODES and clicked_code != st.session_state.last_requested_code:
    st.session_state.selected_country_code = clicked_code
    st.session_state.snapshot = fetch_backend_snapshot(clicked_code, backend_url)
    st.session_state.last_requested_code = clicked_code
    st.rerun()

st.caption(
    f"Countries initialized: {len(ISO3_CODES)} | Snapshot Time: {st.session_state.snapshot.get('time', 'N/A')} | "
    f"Last Clicked Country: {st.session_state.selected_country_code}"
)
