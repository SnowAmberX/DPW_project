from age_risk_chart import build as build_age_risk
from heatmap_chart import build as build_heatmap
from mortality_stats_tables import build as build_mortality_stats
from ranking_chart import build as build_ranking
from scatter_chart import build as build_scatter
from timeline_chart import build as build_timeline


def main() -> None:
    build_scatter()
    build_timeline()
    build_heatmap()
    build_ranking()
    build_age_risk()
    build_mortality_stats()


if __name__ == "__main__":
    main()
