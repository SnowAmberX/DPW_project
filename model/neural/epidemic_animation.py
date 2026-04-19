import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


REQUIRED_COLUMNS = {
    "day",
    "forecast_date",
    "country_code",
    "country_name",
    "seed_country_code",
    "predicted_new_cases",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build choropleth-based global epidemic spread simulation from forecast CSV."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        default="output/outbreak_forecast.csv",
        help="Input forecast CSV file.",
    )
    parser.add_argument(
        "--countries-meta",
        type=str,
        default="artifacts/countries_meta.json",
        help="Country metadata JSON with ISO3 and [lat, lon].",
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default="plague_style_animation.html",
        help="Output interactive HTML path.",
    )
    parser.add_argument(
        "--colorscale",
        type=str,
        default="Reds",
        choices=["Reds", "Viridis", "Plasma", "Cividis", "Turbo"],
        help="Perceptually clear continuous color scale.",
    )
    parser.add_argument(
        "--clip-quantile",
        type=float,
        default=0.995,
        help="Upper quantile for clipping extreme values (0 to disable).",
    )
    parser.add_argument(
        "--speed-km-per-day",
        type=float,
        default=800.0,
        help="Propagation speed (km/day) used to compute infection delay.",
    )
    parser.add_argument(
        "--wave-sigma",
        type=float,
        default=10.0,
        help="Gaussian wave sigma in days. Set <= 0 to disable wave sharpening.",
    )
    parser.add_argument(
        "--frame-duration",
        type=int,
        default=260,
        help="Animation frame duration in milliseconds.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open interactive window after export.",
    )
    return parser.parse_args()


def _validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"Input CSV is missing required columns: {missing_cols}")


def _resolve_input_path(path_str: str, script_dir: Path) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    script_candidate = (script_dir / candidate).resolve()
    if script_candidate.exists():
        return script_candidate

    return cwd_candidate


def _resolve_output_path(path_str: str, script_dir: Path) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.parent.exists():
        return cwd_candidate

    return (script_dir / candidate).resolve()


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-x))


def _haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    lat1_r = np.deg2rad(lat1)
    lon1_r = np.deg2rad(lon1)
    lat2_r = np.deg2rad(lat2)
    lon2_r = np.deg2rad(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return r * c


def load_country_coordinates(meta_path: Path) -> dict[str, tuple[float, float]]:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    rows = [
        (str(item.get("cca3", "")).upper().strip(), item.get("latlng", []))
        for item in data
    ]
    valid_rows = [
        (code, float(latlng[0]), float(latlng[1]))
        for code, latlng in rows
        if code and isinstance(latlng, list) and len(latlng) >= 2
    ]
    return {code: (lat, lon) for code, lat, lon in valid_rows}


def load_and_preprocess(csv_path: Path, clip_quantile: float) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(csv_path)
    _validate_columns(df)

    df = df.copy()
    df["day"] = pd.to_numeric(df["day"], errors="coerce").fillna(0).astype(int)
    df["forecast_date"] = pd.to_datetime(df["forecast_date"], errors="coerce")
    df["forecast_date"] = df["forecast_date"].dt.strftime("%Y-%m-%d")
    df["predicted_new_cases"] = (
        pd.to_numeric(df["predicted_new_cases"], errors="coerce")
        .fillna(0.0)
        .clip(lower=0.0)
    )
    df["country_code"] = df["country_code"].astype(str).str.upper().str.strip()
    df["country_name"] = df["country_name"].astype(str).str.strip()
    df["seed_country_code"] = df["seed_country_code"].astype(str).str.upper().str.strip()

    seed_candidates = df.loc[df["seed_country_code"].ne(""), "seed_country_code"]
    seed_code = (
        seed_candidates.mode().iat[0]
        if not seed_candidates.empty
        else "UNK"
    )

    countries = (
        df[["country_code", "country_name"]]
        .drop_duplicates(subset=["country_code"])
        .sort_values("country_code")
    )
    days = (
        df[["day", "forecast_date"]]
        .drop_duplicates(subset=["day"])
        .sort_values("day")
    )

    daily = (
        df.groupby(["day", "country_code"], as_index=False)["predicted_new_cases"]
        .sum()
    )

    all_pairs = pd.MultiIndex.from_product(
        [days["day"].to_numpy(), countries["country_code"].to_numpy()],
        names=["day", "country_code"],
    ).to_frame(index=False)

    full_df = (
        all_pairs
        .merge(days, on="day", how="left")
        .merge(countries, on="country_code", how="left")
        .merge(daily, on=["day", "country_code"], how="left")
    )

    full_df["predicted_new_cases"] = full_df["predicted_new_cases"].fillna(0.0)

    if 0.0 < clip_quantile < 1.0:
        clip_max = float(full_df["predicted_new_cases"].quantile(clip_quantile))
        full_df["predicted_new_cases"] = full_df["predicted_new_cases"].clip(upper=clip_max)

    full_df["log_cases"] = np.log10(full_df["predicted_new_cases"] + 1.0)
    full_df["seed_country_code"] = seed_code

    return full_df, str(seed_code)


def apply_spread_model(
    df: pd.DataFrame,
    country_coords: dict[str, tuple[float, float]],
    seed_code: str,
    speed_km_per_day: float,
    wave_sigma: float,
) -> tuple[pd.DataFrame, str]:
    out = df.copy()

    lat_map = {code: coord[0] for code, coord in country_coords.items()}
    lon_map = {code: coord[1] for code, coord in country_coords.items()}

    out["lat"] = out["country_code"].map(lat_map)
    out["lon"] = out["country_code"].map(lon_map)

    if seed_code not in country_coords:
        valid_seed_series = out.loc[out["country_code"].isin(country_coords.keys()), "country_code"]
        if valid_seed_series.empty:
            raise ValueError("No overlap between forecast country codes and coordinate metadata.")
        seed_code = str(valid_seed_series.iloc[0])

    seed_lat, seed_lon = country_coords[seed_code]

    lat_vals = out["lat"].to_numpy(dtype=np.float64)
    lon_vals = out["lon"].to_numpy(dtype=np.float64)
    valid = np.isfinite(lat_vals) & np.isfinite(lon_vals)

    distances = np.full(out.shape[0], 20000.0, dtype=np.float64)
    if np.any(valid):
        distances[valid] = _haversine_km(
            float(seed_lat),
            float(seed_lon),
            lat_vals[valid],
            lon_vals[valid],
        )

    speed = max(1.0, float(speed_km_per_day))
    delays = distances / speed

    t = out["day"].to_numpy(dtype=np.float64)
    activation = _sigmoid(t - delays)

    spread_cases = out["predicted_new_cases"].to_numpy(dtype=np.float64) * activation

    if wave_sigma > 0.0:
        sigma = float(wave_sigma)
        wave = np.exp(-((t - delays) ** 2) / (2.0 * sigma * sigma))
        spread_cases = spread_cases * wave

    spread_cases = np.clip(spread_cases, 0.0, None)

    out["distance"] = distances
    out["delay"] = delays
    out["activation"] = activation
    out["spread_cases"] = spread_cases
    out["log_cases"] = np.log10(spread_cases + 1.0)
    out["seed_country_code"] = seed_code

    return out, seed_code


def build_animated_figure(
    spread_df: pd.DataFrame,
    seed_code: str,
    colorscale: str,
    frame_duration: int,
) -> go.Figure:
    day_date = (
        spread_df[["day", "forecast_date"]]
        .drop_duplicates(subset=["day"])
        .sort_values("day")
    )
    day_to_date = dict(zip(day_date["day"], day_date["forecast_date"]))
    day_min = int(day_date["day"].min())
    first_date = day_to_date.get(day_min, "")

    fig = px.choropleth(
        spread_df,
        locations="country_code",
        locationmode="ISO-3",
        color="log_cases",
        animation_frame="day",
        color_continuous_scale=colorscale,
        hover_name="country_name",
        custom_data=[
            "forecast_date",
            "predicted_new_cases",
            "spread_cases",
            "distance",
            "activation",
        ],
        projection="natural earth",
    )

    hover_template = (
        "<b>%{hovertext}</b><br>"
        "Date: %{customdata[0]}<br>"
        "Predicted Cases: %{customdata[1]:,.2f}<br>"
        "Spread Cases: %{customdata[2]:,.2f}<br>"
        "Distance to Seed: %{customdata[3]:,.0f} km<br>"
        "Activation: %{customdata[4]:.3f}<extra></extra>"
    )

    fig.update_traces(hovertemplate=hover_template)

    rebuilt_frames: list[go.Frame] = []
    for raw_frame in list(fig.frames):
        if isinstance(raw_frame, go.Frame):
            frame_payload: dict[str, Any] = raw_frame.to_plotly_json()
        else:
            frame_payload = dict(raw_frame)

        frame_name = str(frame_payload.get("name", day_min))
        try:
            day_value = int(frame_name)
        except ValueError:
            day_value = day_min

        frame_data = frame_payload.get("data", [])
        if isinstance(frame_data, list):
            for trace_payload in frame_data:
                if isinstance(trace_payload, dict):
                    trace_payload["hovertemplate"] = hover_template

        date_value = day_to_date.get(day_value, "")
        frame_payload["layout"] = {
            "title": {
                "text": f"Global Spread Simulation (Seed: {seed_code}) - Day {day_value} ({date_value})"
            }
        }

        rebuilt_frames.append(go.Frame(**frame_payload))

    fig.frames = tuple(rebuilt_frames)

    fig.update_layout(
        title=f"Global Spread Simulation (Seed: {seed_code}) - Day {day_min} ({first_date})",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font={"color": "#EAEAEA"},
        geo={
            "showframe": False,
            "showcoastlines": True,
            "coastlinecolor": "#555",
            "showland": True,
            "landcolor": "#111",
            "showocean": True,
            "oceancolor": "#030303",
            "showlakes": True,
            "lakecolor": "#030303",
            "bgcolor": "black",
            "projection_type": "natural earth",
        },
        coloraxis_colorbar={"title": "log10(spread_cases + 1)"},
        margin={"l": 10, "r": 10, "t": 70, "b": 10},
    )

    if fig.layout.updatemenus and len(fig.layout.updatemenus) > 0:
        play_button = fig.layout.updatemenus[0].buttons[0]
        play_button.args[1]["frame"]["duration"] = int(frame_duration)
        play_button.args[1]["frame"]["redraw"] = True
        play_button.args[1]["transition"]["duration"] = max(60, int(frame_duration * 0.3))

    if fig.layout.sliders and len(fig.layout.sliders) > 0:
        fig.layout.sliders[0]["currentvalue"] = {"prefix": "Day: "}

    return fig


def main() -> None:
    args = parse_args()

    script_dir = Path(__file__).resolve().parent
    input_csv = _resolve_input_path(args.input_csv, script_dir)
    countries_meta = _resolve_input_path(args.countries_meta, script_dir)
    output_html = _resolve_output_path(args.output_html, script_dir)
    output_html.parent.mkdir(parents=True, exist_ok=True)

    full_df, seed_code = load_and_preprocess(input_csv, clip_quantile=args.clip_quantile)
    country_coords = load_country_coordinates(countries_meta)
    spread_df, seed_code = apply_spread_model(
        df=full_df,
        country_coords=country_coords,
        seed_code=seed_code,
        speed_km_per_day=args.speed_km_per_day,
        wave_sigma=float(args.wave_sigma),
    )

    fig = build_animated_figure(
        spread_df=spread_df,
        seed_code=seed_code,
        colorscale=args.colorscale,
        frame_duration=args.frame_duration,
    )

    fig.write_html(str(output_html), include_plotlyjs=True, full_html=True, auto_play=False)
    if args.show:
        fig.show()

    print(f"Saved animation HTML: {output_html}")


if __name__ == "__main__":
    main()
