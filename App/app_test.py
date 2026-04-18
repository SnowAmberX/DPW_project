from datetime import datetime
import json
import math
import time
from urllib import error, request

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(layout="wide", page_title="Global COVID Map")

BACKEND_DEFAULT_URL = "http://127.0.0.1:8000/api/v1/infections/snapshot"
COUNTRY_METADATA_URL = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"
SPREAD_FRAME_INTERVAL_SECONDS = 0.09

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


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def load_country_centroids() -> dict[str, tuple[float, float]]:
    """拉取国家中心点，用于按空间距离做扩散动画。"""
    req = request.Request(
        url=COUNTRY_METADATA_URL,
        headers={"User-Agent": "DPW-Global-COVID-Map"},
    )

    try:
        with request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, TimeoutError, ValueError):
        return {}

    centroids: dict[str, tuple[float, float]] = {}
    for item in payload:
        code = str(item.get("cca3", "")).upper()
        latlng = item.get("latlng", [])

        if code not in ISO3_CODES or not isinstance(latlng, list) or len(latlng) < 2:
            continue

        try:
            lat = float(latlng[0])
            lon = float(latlng[1])
        except (TypeError, ValueError):
            continue

        centroids[code] = (lat, lon)

    return centroids


def haversine_distance_km(origin: tuple[float, float], target: tuple[float, float]) -> float:
    lat1, lon1 = origin
    lat2, lon2 = target

    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (math.sin(dlat / 2) ** 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2) ** 2)
    a = min(1.0, max(0.0, a))

    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


def add_risk_labels(df: pd.DataFrame) -> pd.DataFrame:
    labeled = df.copy()

    max_cases = float(labeled["cases"].max())
    if max_cases <= 0:
        max_cases = 1.0

    labeled["risk_level"] = pd.cut(
        labeled["cases"],
        bins=[-1, max_cases * 0.05, max_cases * 0.2, max_cases * 0.5, max_cases],
        labels=["Low", "Medium", "High", "Very High"],
    ).astype(str)

    return labeled


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

    return add_risk_labels(df)


def build_spread_frame(map_df: pd.DataFrame, origin_code: str | None, progress: float) -> pd.DataFrame:
    if not origin_code:
        return map_df

    centroids = load_country_centroids()
    origin = centroids.get(origin_code)
    if origin is None:
        return map_df

    animated = map_df[["code", "cases"]].copy()

    distances: list[float] = []
    finite_distances: list[float] = []
    for code in animated["code"]:
        target = centroids.get(str(code))
        if target is None:
            distances.append(float("inf"))
            continue

        dist = haversine_distance_km(origin, target)
        distances.append(dist)
        finite_distances.append(dist)

    if not finite_distances:
        return map_df

    max_distance = max(finite_distances)
    if max_distance <= 0:
        return map_df

    clipped_progress = min(max(progress, 0.0), 1.0)
    reveal_limit = clipped_progress * max_distance
    front_width = max(max_distance * 0.08, 350.0)

    weights: list[float] = []
    for dist in distances:
        if not math.isfinite(dist):
            weights.append(clipped_progress)
            continue

        if dist <= reveal_limit:
            weights.append(1.0)
            continue

        if dist >= reveal_limit + front_width:
            weights.append(0.0)
            continue

        weights.append(1.0 - ((dist - reveal_limit) / front_width))

    animated["cases"] = animated["cases"] * pd.Series(weights, index=animated.index, dtype="float64")
    animated.loc[animated["code"] == origin_code, "cases"] = map_df.loc[map_df["code"] == origin_code, "cases"]

    return add_risk_labels(animated)


def create_map_figure(map_df: pd.DataFrame, reference_z_max: float | None = None) -> go.Figure:
    z_max = max(float(reference_z_max if reference_z_max is not None else map_df["cases"].max()), 1.0)

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
            hovertemplate=(
                "Country Code: %{location}<br>"
                "Rendered Cases: %{z:.0f}<br>"
                "Risk Level: %{customdata[0]}<extra></extra>"
            ),
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

    st.divider()
    st.header("Spread Animation")
    spread_enabled = st.checkbox("Enable diffusion animation", value=True)
    spread_duration_seconds = st.slider(
        "Animation duration (seconds)",
        min_value=1.0,
        max_value=8.0,
        value=2.4,
        step=0.2,
    )
    st.caption("The map reveals countries outward from the clicked country by distance.")

if "snapshot" not in st.session_state:
    st.session_state.snapshot = {
        "time": datetime.now().strftime("%Y:%m:%d"),
        "infections_by_country": {},
    }
if "selected_country_code" not in st.session_state:
    st.session_state.selected_country_code = "USA"
if "last_requested_code" not in st.session_state:
    st.session_state.last_requested_code = None
if "spread_origin_code" not in st.session_state:
    st.session_state.spread_origin_code = "USA"
if "spread_started_at" not in st.session_state:
    st.session_state.spread_started_at = 0.0
if "spread_progress" not in st.session_state:
    st.session_state.spread_progress = 1.0
if "is_spread_animating" not in st.session_state:
    st.session_state.is_spread_animating = False

if st.session_state.last_requested_code is None:
    st.session_state.snapshot = fetch_backend_snapshot(
        st.session_state.selected_country_code,
        backend_url,
    )
    st.session_state.last_requested_code = st.session_state.selected_country_code
    st.session_state.spread_origin_code = st.session_state.selected_country_code
    st.session_state.spread_progress = 1.0
    st.session_state.is_spread_animating = False

base_map_df = build_map_frame(st.session_state.snapshot)
display_map_df = base_map_df
event = None

if spread_enabled and st.session_state.is_spread_animating:
    frame_count = max(int(spread_duration_seconds / SPREAD_FRAME_INTERVAL_SECONDS), 1)
    chart_placeholder = st.empty()

    for frame_idx in range(frame_count + 1):
        progress = frame_idx / frame_count
        st.session_state.spread_progress = progress

        display_map_df = build_spread_frame(
            base_map_df,
            st.session_state.spread_origin_code,
            progress,
        )
        frame_fig = create_map_figure(display_map_df, reference_z_max=float(base_map_df["cases"].max()))
        chart_placeholder.plotly_chart(frame_fig, width='stretch')

        if frame_idx < frame_count:
            time.sleep(SPREAD_FRAME_INTERVAL_SECONDS)

    st.session_state.is_spread_animating = False
    st.session_state.spread_progress = 1.0
    st.rerun()
else:
    if spread_enabled and st.session_state.spread_origin_code:
        display_map_df = build_spread_frame(base_map_df, st.session_state.spread_origin_code, 1.0)
        st.session_state.spread_progress = 1.0
    else:
        st.session_state.is_spread_animating = False
        st.session_state.spread_progress = 1.0

    fig = create_map_figure(display_map_df, reference_z_max=float(base_map_df["cases"].max()))

    try:
        event = st.plotly_chart(
            fig,
            width='stretch',
            key="infection_world_map",
            on_select="rerun",
        )
    except TypeError:
        st.warning("Your current Streamlit version does not support click selection on Plotly charts.")
        st.plotly_chart(fig, width='stretch', key="infection_world_map_fallback")
        event = None

clicked_code = extract_selected_code(event)
if clicked_code and clicked_code in ISO3_CODES and clicked_code != st.session_state.last_requested_code:
    st.session_state.selected_country_code = clicked_code
    st.session_state.snapshot = fetch_backend_snapshot(clicked_code, backend_url)
    st.session_state.last_requested_code = clicked_code

    st.session_state.spread_origin_code = clicked_code
    if spread_enabled:
        st.session_state.spread_started_at = time.perf_counter()
        st.session_state.spread_progress = 0.0
        st.session_state.is_spread_animating = True
    else:
        st.session_state.spread_progress = 1.0
        st.session_state.is_spread_animating = False

    st.rerun()

st.caption(
    f"Countries initialized: {len(ISO3_CODES)} | Snapshot Time: {st.session_state.snapshot.get('time', 'N/A')} | "
    f"Last Clicked Country: {st.session_state.selected_country_code} | "
    f"Spread Progress: {int(st.session_state.spread_progress * 100)}%"
)
