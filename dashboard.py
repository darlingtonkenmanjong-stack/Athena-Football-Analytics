import json
import time
import streamlit as st
import pandas as pd
from pathlib import Path


st.set_page_config(
    page_title="Football Player Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            linear-gradient(
                rgba(0, 28, 14, 0.88),
                rgba(0, 18, 9, 0.94)
            ),
            repeating-linear-gradient(
                90deg,
                #176b38 0px,
                #176b38 120px,
                #1d7740 120px,
                #1d7740 240px
            );
        background-attachment: fixed;
    }

    .block-container {
        max-width: 1550px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: white !important;
    }

    p, label {
        color: #f5f5f5 !important;
    }

    .main-header {
        background:
            linear-gradient(
                90deg,
                rgba(3, 28, 17, 0.97),
                rgba(7, 55, 29, 0.96)
            );

        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 18px;
        padding: 24px 28px;
        margin-bottom: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.28);
    }

    .main-title {
        font-size: clamp(26px, 3vw, 40px);
        font-weight: 900;
        color: white;
    }

    .main-subtitle {
        font-size: clamp(13px, 1.4vw, 16px);
        color: #caead5;
        margin-top: 5px;
    }

    .match-banner {
        background:
            linear-gradient(
                90deg,
                rgba(8, 42, 25, 0.98),
                rgba(11, 83, 40, 0.98),
                rgba(8, 42, 25, 0.98)
            );

        border-radius: 18px;
        padding: 22px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.18);
        box-shadow: 0 7px 25px rgba(0,0,0,0.25);
        margin-bottom: 18px;
    }

    .match-teams {
        color: white;
        font-size: clamp(20px, 2.4vw, 32px);
        font-weight: 900;
    }

    .match-status {
        color: #ccebd6;
        font-size: 14px;
        margin-top: 6px;
    }

    [data-testid="stMetric"] {
        background: rgba(3, 30, 18, 0.95);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 15px;
        padding: 17px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.20);
    }

    [data-testid="stMetricLabel"] {
        color: #ccebd6 !important;
    }

    [data-testid="stMetricValue"] {
        color: white !important;
        font-weight: 800 !important;
    }

    .section-title {
        font-size: clamp(20px, 2vw, 26px);
        font-weight: 850;
        color: white;

        margin-top: 25px;
        margin-bottom: 13px;

        padding-bottom: 8px;

        border-bottom:
            1px solid rgba(255,255,255,0.15);
    }

    .alert-high {
        background:
            linear-gradient(
                90deg,
                rgba(124, 14, 14, 0.96),
                rgba(74, 8, 8, 0.96)
            );

        border-left: 7px solid #ff4b4b;
        border-radius: 14px;
        padding: 17px 20px;
        margin-bottom: 10px;
        color: white;
        box-shadow: 0 5px 18px rgba(0,0,0,0.22);
    }

    .alert-moderate {
        background:
            linear-gradient(
                90deg,
                rgba(113, 65, 5, 0.96),
                rgba(73, 41, 4, 0.96)
            );

        border-left: 7px solid #ffa21a;
        border-radius: 14px;
        padding: 17px 20px;
        margin-bottom: 10px;
        color: white;
        box-shadow: 0 5px 18px rgba(0,0,0,0.22);
    }

    .alert-info {
        background:
            linear-gradient(
                90deg,
                rgba(8, 63, 100, 0.96),
                rgba(5, 40, 66, 0.96)
            );

        border-left: 7px solid #35a7ff;
        border-radius: 14px;
        padding: 17px 20px;
        margin-bottom: 10px;
        color: white;
        box-shadow: 0 5px 18px rgba(0,0,0,0.22);
    }

    .alert-player {
        font-size: 19px;
        font-weight: 850;
        color: white;
    }

    .alert-meta {
        margin-top: 5px;
        font-size: 14px;
        color: #ededed;
    }

    .alert-decision {
        margin-top: 10px;
        color: white;
        font-size: 14px;
    }

    .team-card {
        background: rgba(3, 30, 18, 0.95);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 16px;
        padding: 20px;
        min-height: 170px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.20);
    }

    .team-name {
        font-size: 23px;
        font-weight: 850;
        color: white;
    }

    .team-detail {
        color: #d7eadf;
        margin-top: 9px;
        font-size: 14px;
    }

    .player-card {
        background: rgba(3, 27, 17, 0.96);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.18);
    }

    .player-name {
        color: white;
        font-size: 23px;
        font-weight: 850;
    }

    .player-team {
        color: #ccebd6;
        margin-top: 4px;
    }

    .decision-card {
        background: rgba(4, 28, 18, 0.96);
        border: 1px solid rgba(255,255,255,0.14);
        border-left: 5px solid #4fc375;
        border-radius: 14px;
        padding: 17px 20px;
        margin-bottom: 10px;
    }

    .decision-player {
        color: white;
        font-size: 18px;
        font-weight: 850;
    }

    .decision-text {
        color: #d8eadf;
        margin-top: 5px;
        font-size: 14px;
    }

    .status-live {
        display: inline-block;
        background: rgba(39, 170, 73, 0.20);
        border: 1px solid rgba(64, 220, 104, 0.45);
        border-radius: 20px;
        padding: 6px 12px;
        color: #7cff9c;
        font-weight: 700;
        font-size: 13px;
    }

    .footer {
        text-align: center;
        color: #ccebd6;
        padding: 24px;
        font-size: 14px;
    }

    [data-testid="stSidebar"] {
        background: rgba(3, 24, 14, 0.98);
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* Responsive behaviour */
    @media (max-width: 900px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        .main-header {
            padding: 18px;
        }

        .match-banner {
            padding: 17px;
        }

        .alert-high,
        .alert-moderate,
        .alert-info,
        .team-card,
        .player-card,
        .decision-card {
            padding: 14px;
        }
    }

    @media (max-width: 600px) {

        .main-title {
            font-size: 25px;
        }

        .match-teams {
            font-size: 19px;
        }

        .section-title {
            font-size: 20px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# LIVE DATA
# =========================================================

state_file = Path("live_dashboard_state.json")
forecast_file = Path("live_halftime_forecasts.csv")
alerts_file = Path("live_alert_popups.csv")
decision_file = Path("live_halftime_decision_support.csv")


def read_live_state():
    if not state_file.exists():
        return None

    try:
        with state_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):
        return None


def records_to_dataframe(records):
    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def load_fallback_csv(path):
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


state = read_live_state()

if state is None:
    st.warning(
        "Waiting for live match state from "
        "model_inference.py..."
    )

    time.sleep(1)
    st.rerun()


forecasts = records_to_dataframe(
    state.get("forecasts", [])
)

alerts = records_to_dataframe(
    state.get("popup_alerts", [])
)

active_alerts = records_to_dataframe(
    state.get("active_alerts", [])
)

assessments = records_to_dataframe(
    state.get("player_assessments", [])
)

decisions = records_to_dataframe(
    state.get("decisions", [])
)


if forecasts.empty and state.get(
    "halftime_complete",
    False
):
    forecasts = load_fallback_csv(
        forecast_file
    )


if alerts.empty:
    alerts = load_fallback_csv(
        alerts_file
    )


if decisions.empty and state.get(
    "halftime_complete",
    False
):
    decisions = load_fallback_csv(
        decision_file
    )


match_minute = int(
    state.get("match_minute", 0) or 0
)

match_second = int(
    state.get("match_second", 0) or 0
)

match_clock = (
    f"{match_minute:02d}:"
    f"{match_second:02d}"
)

match_stage = state.get(
    "match_stage",
    "Pre-Match"
)

system_status = state.get(
    "system_status",
    "Waiting"
)

event_count = int(
    state.get("event_count", 0) or 0
)

halftime_complete = bool(
    state.get(
        "halftime_complete",
        False
    )
)

stream_complete = bool(
    state.get(
        "stream_complete",
        False
    )
)


if "seen_popup_ids" not in st.session_state:
    st.session_state.seen_popup_ids = set()


for popup in state.get(
    "popup_alerts",
    []
):
    popup_id = (
        f'{popup.get("checkpoint", "")}|'
        f'{popup.get("player_id", "")}|'
        f'{popup.get("category", "")}|'
        f'{popup.get("severity", "")}|'
        f'{popup.get("popup_reason", "")}'
    )

    if (
        popup_id
        not in st.session_state.seen_popup_ids
    ):
        st.session_state.seen_popup_ids.add(
            popup_id
        )

        severity = popup.get(
            "severity",
            "Informational"
        )

        message = (
            f'{popup.get("player_name", "Player")} — '
            f'{popup.get("category", "Alert")}: '
            f'{popup.get("message", "")}'
        )

        if severity in [
            "Critical",
            "High"
        ]:
            st.error(message)

        elif severity == "Moderate":
            st.warning(message)

        else:
            st.info(message)


# =========================================================
# HEADER
# =========================================================

header_html = (
    '<div class="main-header">'
    '<div class="main-title">⚽ Football Player Intelligence</div>'
    '<div class="main-subtitle">'
    'Real-Time Player Assessment • Contextual Machine Learning • '
    'Performance Forecasting • Tactical Decision Support'
    '</div>'
    '</div>'
)

st.markdown(
    header_html,
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "⚽ Match Controls"
)


st.sidebar.markdown(
    f'<span class="status-live">● SYSTEM {system_status.upper()}</span>',
    unsafe_allow_html=True
)


st.sidebar.divider()


team_source = forecasts.copy()

if team_source.empty:
    team_source = assessments.copy()

if team_source.empty:
    team_source = active_alerts.copy()


if (
    not team_source.empty
    and "team" in team_source.columns
):
    live_teams = sorted(
        team_source["team"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
else:
    live_teams = [
        "Barcelona",
        "Elche"
    ]


team_options = [
    "All"
] + live_teams


selected_team = st.sidebar.selectbox(
    "Team",
    team_options
)


if (
    not team_source.empty
    and "player_name"
    in team_source.columns
):
    player_source = team_source.copy()

    if (
        selected_team != "All"
        and "team"
        in player_source.columns
    ):
        player_source = player_source[
            player_source["team"]
            == selected_team
        ]

    available_players = sorted(
        player_source[
            "player_name"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

else:
    available_players = []


player_options = [
    "All Players"
] + available_players


selected_player = (
    st.sidebar.selectbox(
        "Player",
        player_options
    )
)


severity_filter = (
    st.sidebar.multiselect(
        "Alert Severity",
        [
            "Critical",
            "High",
            "Moderate",
            "Informational"
        ],
        default=[
            "Critical",
            "High",
            "Moderate",
            "Informational"
        ]
    )
)


st.sidebar.divider()


st.sidebar.caption(
    "Use these controls to explore "
    "team, player and tactical information."
)


# =========================================================
# MATCH BANNER
# =========================================================

match_html = (
    '<div class="match-banner">'
    '<div class="match-teams">'
    '🔵🔴 Barcelona'
    '&nbsp;&nbsp; ⚽ &nbsp;&nbsp;'
    'Elche 🟢'
    '</div>'
    '<div class="match-status">'
    f'{match_stage} &nbsp; • &nbsp; '
    f'{match_clock} &nbsp; • &nbsp; '
    f'{event_count:,} events processed'
    '<br>'
    'Replay-Based Real-Time Football Intelligence'
    '</div>'
    '</div>'
)


st.markdown(
    match_html,
    unsafe_allow_html=True
)


# =========================================================
# MAIN METRICS
# =========================================================

priority_source = active_alerts.copy()

if priority_source.empty:
    priority_source = decisions.copy()


if (
    not priority_source.empty
    and "player_id"
    in priority_source.columns
):
    priority_players = (
        priority_source[
            "player_id"
        ].nunique()
    )

elif (
    not priority_source.empty
    and "player_name"
    in priority_source.columns
):
    priority_players = (
        priority_source[
            "player_name"
        ].nunique()
    )

else:
    priority_players = 0


players_tracked = 0

if not assessments.empty:
    players_tracked = len(assessments)

elif not forecasts.empty:
    players_tracked = len(forecasts)


m1, m2, m3, m4, m5 = (
    st.columns(5)
)


with m1:
    st.metric(
        "⏱ Match Clock",
        match_clock
    )


with m2:
    st.metric(
        "🏟 Match Stage",
        match_stage
    )


with m3:
    st.metric(
        "📡 System",
        system_status
    )


with m4:
    st.metric(
        "👥 Players",
        players_tracked
    )


with m5:
    st.metric(
        "🚨 Priority Players",
        priority_players
    )


# =========================================================
# TABS
# =========================================================

tab_overview, tab_players, tab_alerts, tab_forecast, tab_decisions = (
    st.tabs(
        [
            "⚽ Overview",
            "👤 Players",
            "🚨 Alerts",
            "🔮 Forecast",
            "🧠 Decisions"
        ]
    )
)


# =========================================================
# OVERVIEW TAB
# =========================================================

with tab_overview:

    st.markdown(
        '<div class="section-title">'
        '⚽ Team Intelligence'
        '</div>',
        unsafe_allow_html=True
    )


    overview_players = forecasts.copy()

    if overview_players.empty:
        overview_players = assessments.copy()

    if (
        not overview_players.empty
        and "team"
        in overview_players.columns
    ):
        barcelona = overview_players[
            overview_players["team"]
            == "Barcelona"
        ]

        elche = overview_players[
            overview_players["team"]
            == "Elche"
        ]

    else:
        barcelona = pd.DataFrame()
        elche = pd.DataFrame()


    team_left, team_right = (
        st.columns(2)
    )


    with team_left:

        html = (
            '<div class="team-card">'
            '<div class="team-name">'
            '🔵🔴 Barcelona'
            '</div>'
            '<div class="team-detail">'
            f'👥 Players monitored: {len(barcelona)}'
            '</div>'
            '<div class="team-detail">'
            '📡 Contextual pass assessment active'
            '</div>'
            '<div class="team-detail">'
            '🔮 Second-half forecasting active'
            '</div>'
            '<div class="team-detail">'
            '🧠 Tactical decision support active'
            '</div>'
            '</div>'
        )

        st.markdown(
            html,
            unsafe_allow_html=True
        )


    with team_right:

        html = (
            '<div class="team-card">'
            '<div class="team-name">'
            '🟢 Elche'
            '</div>'
            '<div class="team-detail">'
            f'👥 Players monitored: {len(elche)}'
            '</div>'
            '<div class="team-detail">'
            '📡 Contextual pass assessment active'
            '</div>'
            '<div class="team-detail">'
            '🔮 Second-half forecasting active'
            '</div>'
            '<div class="team-detail">'
            '🧠 Tactical decision support active'
            '</div>'
            '</div>'
        )

        st.markdown(
            html,
            unsafe_allow_html=True
        )


    st.markdown(
        '<div class="section-title">'
        '🚨 Current Priority Alerts'
        '</div>',
        unsafe_allow_html=True
    )


    if not decisions.empty:
        overview_decisions = decisions.copy()

    else:
        overview_decisions = active_alerts.copy()

        if (
            not overview_decisions.empty
            and "category"
            in overview_decisions.columns
        ):
            overview_decisions[
                "alert_categories"
            ] = overview_decisions[
                "category"
            ]

            overview_decisions[
                "recommendation"
            ] = "Monitor"


    if selected_team != "All":

        overview_decisions = (
            overview_decisions[
                overview_decisions[
                    "team"
                ] == selected_team
            ]
        )


    if selected_player != "All Players":

        overview_decisions = (
            overview_decisions[
                overview_decisions[
                    "player_name"
                ] == selected_player
            ]
        )


    severity_order = {
        "Critical": 4,
        "High": 3,
        "Moderate": 2,
        "Informational": 1
    }


    if (
        not overview_decisions.empty
        and "severity" in overview_decisions.columns
    ):
        overview_decisions = (
            overview_decisions[
                overview_decisions[
                    "severity"
                ].isin(
                    severity_filter
                )
            ]
        )

        overview_decisions[
            "_priority"
        ] = (
            overview_decisions[
                "severity"
            ]
            .map(
                severity_order
            )
            .fillna(0)
        )

        overview_decisions = (
            overview_decisions
            .sort_values(
                "_priority",
                ascending=False
            )
        )


    if overview_decisions.empty:

        st.success(
            "No alerts match the selected filters."
        )

    else:

        for _, row in (
            overview_decisions.iterrows()
        ):

            severity = str(
                row.get(
                    "severity",
                    "Informational"
                )
            )


            if severity in [
                "Critical",
                "High"
            ]:

                css_class = "alert-high"
                icon = "🔴"


            elif severity == "Moderate":

                css_class = (
                    "alert-moderate"
                )

                icon = "🟠"


            else:

                css_class = (
                    "alert-info"
                )

                icon = "🔵"


            player = row.get(
                "player_name",
                "Unknown Player"
            )


            team = row.get(
                "team",
                ""
            )


            category = row.get(
                "alert_categories",
                ""
            )


            recommendation = row.get(
                "recommendation",
                ""
            )


            alert_html = (
                f'<div class="{css_class}">'
                f'<div class="alert-player">'
                f'{icon} {player}'
                f'</div>'
                f'<div class="alert-meta">'
                f'{team} &nbsp; • &nbsp; '
                f'{severity} &nbsp; • &nbsp; '
                f'{category}'
                f'</div>'
                f'<div class="alert-decision">'
                f'<strong>🧠 Decision Support:</strong> '
                f'{recommendation}'
                f'</div>'
                f'</div>'
            )


            st.markdown(
                alert_html,
                unsafe_allow_html=True
            )


# =========================================================
# PLAYER TAB
# =========================================================

with tab_players:

    if forecasts.empty:
        st.info(
            "Second-half player forecasts become "
            "available automatically at halftime."
        )

    st.markdown(
        '<div class="section-title">'
        '👤 Player Intelligence'
        '</div>',
        unsafe_allow_html=True
    )


    player_name_source = forecasts.copy()

    if player_name_source.empty:
        player_name_source = assessments.copy()

    if (
        not player_name_source.empty
        and "player_name"
        in player_name_source.columns
    ):
        player_names = (
            player_name_source[
                "player_name"
            ]
            .dropna()
            .sort_values()
            .unique()
        )

    else:
        player_names = []


    default_index = 0


    if (
        selected_player
        != "All Players"
        and selected_player
        in player_names
    ):

        default_index = (
            list(player_names)
            .index(
                selected_player
            )
        )


    player_selected = (
        st.selectbox(
            "Select player to analyse",
            player_names,
            index=default_index
        )
    )


    if (
        not forecasts.empty
        and "player_name"
        in forecasts.columns
    ):
        player_data = (
            forecasts[
                forecasts[
                    "player_name"
                ] == player_selected
            ]
        )

    else:
        player_data = pd.DataFrame()


    if not player_data.empty:

        row = (
            player_data.iloc[0]
        )


        player_html = (
            '<div class="player-card">'
            '<div class="player-name">'
            f'⚽ {player_selected}'
            '</div>'
            '<div class="player-team">'
            f'{row.get("team", "")}'
            '</div>'
            '</div>'
        )


        st.markdown(
            player_html,
            unsafe_allow_html=True
        )


        p1, p2, p3, p4, p5 = (
            st.columns(5)
        )


        with p1:

            st.metric(
                "Actions / 90",
                f'{row.get("second_half_actions_per90", 0):.2f}'
            )


        with p2:

            st.metric(
                "Progressive / 90",
                f'{row.get("second_half_progressive_passes_per90", 0):.2f}'
            )


        pass_rate = (
            row.get(
                "second_half_pass_completion_rate",
                0
            )
        )


        with p3:

            st.metric(
                "Pass Completion",
                f"{pass_rate * 100:.2f}%"
            )


        with p4:

            st.metric(
                "Miscontrols / 90",
                f'{row.get("second_half_miscontrols_per90", 0):.2f}'
            )


        with p5:

            st.metric(
                "xG / 90",
                f'{row.get("second_half_statsbomb_xg_per90", 0):.2f}'
            )


        st.markdown(
            '<div class="section-title">'
            '📊 Forecast Profile'
            '</div>',
            unsafe_allow_html=True
        )


        chart_data = pd.DataFrame(
            {
                "Metric": [
                    "Progressive passes / 90",
                    "Miscontrols / 90",
                    "xG / 90"
                ],

                "Value": [
                    row.get(
                        "second_half_progressive_passes_per90",
                        0
                    ),

                    row.get(
                        "second_half_miscontrols_per90",
                        0
                    ),

                    row.get(
                        "second_half_statsbomb_xg_per90",
                        0
                    )
                ]
            }
        )


        st.bar_chart(
            chart_data,
            x="Metric",
            y="Value"
        )


        player_alerts = (
            decisions[
                decisions[
                    "player_name"
                ] == player_selected
            ]
        )


        if not player_alerts.empty:

            st.markdown(
                '<div class="section-title">'
                '🚨 Player Alerts'
                '</div>',
                unsafe_allow_html=True
            )


            for _, alert in (
                player_alerts.iterrows()
            ):

                with st.expander(
                    f'{alert.get("severity", "")}'
                    f' — '
                    f'{alert.get("alert_categories", "")}'
                ):

                    st.write(
                        "**Recommendation:**",
                        alert.get(
                            "recommendation",
                            ""
                        )
                    )

                    st.write(
                        "**Team:**",
                        alert.get(
                            "team",
                            ""
                        )
                    )


# =========================================================
# ALERT TAB
# =========================================================

with tab_alerts:

    st.markdown(
        '<div class="section-title">'
        '🚨 Alert Centre'
        '</div>',
        unsafe_allow_html=True
    )


    filtered_alerts = active_alerts.copy()

    if filtered_alerts.empty:
        filtered_alerts = alerts.copy()


    if selected_team != "All":

        filtered_alerts = (
            filtered_alerts[
                filtered_alerts[
                    "team"
                ] == selected_team
            ]
        )


    if selected_player != "All Players":

        filtered_alerts = (
            filtered_alerts[
                filtered_alerts[
                    "player_name"
                ] == selected_player
            ]
        )


    if "severity" in filtered_alerts.columns:

        filtered_alerts = (
            filtered_alerts[
                filtered_alerts[
                    "severity"
                ].isin(
                    severity_filter
                )
            ]
        )


    if filtered_alerts.empty:

        st.info(
            "No alerts match the selected filters."
        )

    else:

        for _, row in (
            filtered_alerts.iterrows()
        ):

            checkpoint = row.get(
                "checkpoint",
                match_minute
            )


            player = row.get(
                "player_name",
                ""
            )


            category = row.get(
                "category",
                ""
            )


            severity = row.get(
                "severity",
                ""
            )


            title = (
                f"⏱ {checkpoint}'"
                f" — {player}"
                f" — {severity}"
            )


            with st.expander(
                title
            ):

                st.write(
                    "**Team:**",
                    row.get(
                        "team",
                        ""
                    )
                )

                st.write(
                    "**Category:**",
                    category
                )

                st.write(
                    "**Trigger:**",
                    row.get(
                        "popup_reason",
                        ""
                    )
                )

                st.write(
                    "**Explanation:**",
                    row.get(
                        "message",
                        ""
                    )
                )


        alert_table_columns = [
            "checkpoint",
            "player_name",
            "team",
            "severity",
            "category",
            "popup_reason",
            "message"
        ]


        alert_table_columns = [
            column
            for column
            in alert_table_columns
            if column
            in filtered_alerts.columns
        ]


        alert_table = (
            filtered_alerts[
                alert_table_columns
            ].copy()
        )


        alert_table = alert_table.rename(
            columns={
                "checkpoint": "Minute",
                "player_name": "Player",
                "team": "Team",
                "severity": "Severity",
                "category": "Category",
                "popup_reason": "Trigger",
                "message": "Explanation"
            }
        )


        st.dataframe(
            alert_table,
            width="stretch",
            hide_index=True
        )


# =========================================================
# FORECAST TAB
# =========================================================

with tab_forecast:

    st.markdown(
        '<div class="section-title">'
        '🔮 Second-Half Forecast'
        '</div>',
        unsafe_allow_html=True
    )


    forecast_view = (
        forecasts.copy()
    )

    if forecast_view.empty:
        st.info(
            "Forecasting is waiting for the "
            "halftime checkpoint."
        )


    if not forecast_view.empty:
        if selected_team != "All":

            forecast_view = (
                forecast_view[
                    forecast_view[
                        "team"
                    ] == selected_team
                ]
            )


        if selected_player != "All Players":

            forecast_view = (
                forecast_view[
                    forecast_view[
                        "player_name"
                    ] == selected_player
                ]
            )


        display = forecast_view[
            [
                "player_name",
                "team",
                "second_half_actions_per90",
                "second_half_progressive_passes_per90",
                "second_half_pass_completion_rate",
                "second_half_miscontrols_per90",
                "second_half_statsbomb_xg_per90"
            ]
        ].copy()


        display[
            "second_half_pass_completion_rate"
        ] = (
            display[
                "second_half_pass_completion_rate"
            ] * 100
        ).round(2)


        for column in [
            "second_half_actions_per90",
            "second_half_progressive_passes_per90",
            "second_half_miscontrols_per90",
            "second_half_statsbomb_xg_per90"
        ]:

            display[column] = (
                display[
                    column
                ].round(2)
            )


        display = display.rename(
            columns={
                "player_name":
                    "Player",

                "team":
                    "Team",

                "second_half_actions_per90":
                    "Actions / 90",

                "second_half_progressive_passes_per90":
                    "Progressive / 90",

                "second_half_pass_completion_rate":
                    "Pass Completion %",

                "second_half_miscontrols_per90":
                    "Miscontrols / 90",

                "second_half_statsbomb_xg_per90":
                    "xG / 90"
            }
        )


        st.dataframe(
            display,
            width="stretch",
            hide_index=True
        )


        if len(forecast_view) > 1:

            chart_metric = (
                st.selectbox(
                    "Compare players by forecast metric",
                    [
                        "second_half_actions_per90",
                        "second_half_progressive_passes_per90",
                        "second_half_miscontrols_per90",
                        "second_half_statsbomb_xg_per90"
                    ]
                )
            )


            comparison = (
                forecast_view[
                    [
                        "player_name",
                        chart_metric
                    ]
                ]
                .sort_values(
                    chart_metric,
                    ascending=False
                )
            )


            st.bar_chart(
                comparison,
                x="player_name",
                y=chart_metric
            )



# =========================================================
# DECISION SUPPORT TAB
# =========================================================

with tab_decisions:

    st.markdown(
        '<div class="section-title">'
        '🧠 Tactical Decision Support'
        '</div>',
        unsafe_allow_html=True
    )


    if decisions.empty:
        st.info(
            "Tactical decision support becomes "
            "available at halftime after the "
            "forecasting models run."
        )

    else:
        filtered_decisions = (
            decisions.copy()
        )


        if selected_team != "All":

            filtered_decisions = (
                filtered_decisions[
                    filtered_decisions[
                        "team"
                    ] == selected_team
                ]
            )


        if selected_player != "All Players":

            filtered_decisions = (
                filtered_decisions[
                    filtered_decisions[
                        "player_name"
                    ] == selected_player
                ]
            )


        filtered_decisions = (
            filtered_decisions[
                filtered_decisions[
                    "severity"
                ].isin(
                    severity_filter
                )
            ]
        )


        if filtered_decisions.empty:

            st.success(
                "No active tactical recommendations "
                "for the selected filters."
            )

        else:

            for _, row in (
                filtered_decisions.iterrows()
            ):

                player = row.get(
                    "player_name",
                    ""
                )


                team = row.get(
                    "team",
                    ""
                )


                severity = row.get(
                    "severity",
                    ""
                )


                reason = row.get(
                    "alert_categories",
                    ""
                )


                recommendation = row.get(
                    "recommendation",
                    ""
                )


                html = (
                    '<div class="decision-card">'
                    '<div class="decision-player">'
                    f'⚽ {player}'
                    '</div>'
                    '<div class="decision-text">'
                    f'<strong>Team:</strong> {team}'
                    '</div>'
                    '<div class="decision-text">'
                    f'<strong>Priority:</strong> {severity}'
                    '</div>'
                    '<div class="decision-text">'
                    f'<strong>Reason:</strong> {reason}'
                    '</div>'
                    '<div class="decision-text">'
                    f'<strong>Recommendation:</strong> '
                    f'{recommendation}'
                    '</div>'
                    '</div>'
                )


                st.markdown(
                    html,
                    unsafe_allow_html=True
                )



# =========================================================
# SYSTEM ARCHITECTURE
# =========================================================

st.markdown(
    '<div class="section-title">'
    '📡 Real-Time System Architecture'
    '</div>',
    unsafe_allow_html=True
)


a1, a2, a3, a4 = (
    st.columns(4)
)


with a1:

    st.info(
        "📨 EVENT STREAM\n\n"
        "Historical match events are replayed "
        "chronologically."
    )


with a2:

    st.info(
        "⚡ KAFKA + SPARK\n\n"
        "Events move through the streaming "
        "pipeline for processing."
    )


with a3:

    st.info(
        "🧠 MACHINE LEARNING\n\n"
        "xPass assessment and player "
        "forecasting models perform inference."
    )


with a4:

    st.info(
        "🚨 DECISION SUPPORT\n\n"
        "Persistent deviations become "
        "explainable tactical alerts."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()


footer_html = (
    '<div class="footer">'
    '⚽ <strong>Football Analytics Platform</strong>'
    '<br><br>'
    'ASSESS NOW &nbsp; • &nbsp; '
    'PREDICT NEXT &nbsp; • &nbsp; '
    'SUPPORT DECISION'
    '<br><br>'
    'Replay-based real-time decision-support prototype '
    'using StatsBomb Events, StatsBomb 360, '
    'machine learning, historical player baselines '
    'and future-performance forecasting.'
    '</div>'
)


st.markdown(
    footer_html,
    unsafe_allow_html=True
)

if not stream_complete:
    time.sleep(1)
    st.rerun()
