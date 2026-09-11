import json
import math
import joblib
import numpy as np
import pandas as pd

from collections import defaultdict
from kafka import KafkaConsumer
from live_dashboard_state import write_dashboard_state
from ai_decision_engine import build_ai_decision


MATCH_ID = 3764440
TOPIC = "football-processed"
BOOTSTRAP_SERVERS = "localhost:9092"

MIN_FORECAST_MINUTES = 20


xpass_model = joblib.load("xpass_event_360_model.pkl")

forecasting_models = joblib.load(
    "final_player_forecasting_models.pkl"
)

historical_master = pd.read_pickle(
    "historical_player_match_master_corrected.pkl"
)


historical_master["match_id"] = pd.to_numeric(
    historical_master["match_id"],
    errors="coerce"
).astype("Int64")

historical_master["player_id"] = pd.to_numeric(
    historical_master["player_id"],
    errors="coerce"
).astype("Int64")


match_history = historical_master[
    historical_master["match_id"] == MATCH_ID
].copy()


history_lookup = {
    int(player_id): row
    for player_id, row in (
        match_history
        .set_index("player_id")
        .to_dict("index")
        .items()
    )
}


def create_player_state():
    return {
        "team": None,
        "player_name": None,
        "actions": 0,
        "pass_attempts": 0,
        "completed_passes": 0,
        "progressive_passes": 0,
        "xpass_evaluated_passes": 0,
        "xpass_actual_completions": 0,
        "expected_completions": 0.0,
        "shots": 0,
        "goals": 0,
        "statsbomb_xg": 0.0,
        "carries": 0,
        "miscontrols": 0,
        "interceptions": 0,
        "ball_recoveries": 0,
        "dribbles": 0,
        "duels": 0,
        "pressures": 0,
        "shot_assists": 0
    }


def create_segment_state():
    return {
        "actions": 0,
        "pass_attempts": 0,
        "completed_passes": 0,
        "progressive_passes": 0,
        "shots": 0,
        "statsbomb_xg": 0.0,
        "carries": 0,
        "miscontrols": 0,
        "interceptions": 0,
        "ball_recoveries": 0,
        "dribbles": 0,
        "duels": 0,
        "pressures": 0,
        "shot_assists": 0
    }


def create_exposure_record(team, player_name, start_minute):
    return {
        "team": team,
        "player_name": player_name,
        "on_pitch": True,
        "minutes_played": 0.0,
        "early_minutes": 0.0,
        "recent_minutes": 0.0,
        "last_update_minute": start_minute
    }


def initialise_starting_players(raw_event, exposure):
    team = raw_event.get("team", {}).get("name")

    lineup = (
        raw_event
        .get("tactics", {})
        .get("lineup", [])
    )

    for item in lineup:
        player = item.get("player", {})

        player_id = player.get("id")
        player_name = player.get("name")

        if player_id is None:
            continue

        player_id = int(player_id)

        if player_id not in exposure:
            exposure[player_id] = create_exposure_record(
                team=team,
                player_name=player_name,
                start_minute=0.0
            )


def allocate_segment_minutes(player, start_minute, end_minute):
    if end_minute <= start_minute:
        return

    early_start = max(start_minute, 0)
    early_end = min(end_minute, 30)

    if early_end > early_start:
        player["early_minutes"] += (
            early_end - early_start
        )

    recent_start = max(start_minute, 30)
    recent_end = end_minute

    if recent_end > recent_start:
        player["recent_minutes"] += (
            recent_end - recent_start
        )


def advance_first_half_exposure(exposure, current_minute):
    for player in exposure.values():

        if not player["on_pitch"]:
            continue

        previous_minute = player["last_update_minute"]

        delta = current_minute - previous_minute

        if delta <= 0:
            continue

        player["minutes_played"] += delta

        allocate_segment_minutes(
            player,
            previous_minute,
            current_minute
        )

        player["last_update_minute"] = current_minute


def update_first_half_exposure(event, exposure):
    if event.get("period") != 1:
        return

    current_minute = (
        event.get("minute", 0)
        + event.get("second", 0) / 60
    )

    advance_first_half_exposure(
        exposure,
        current_minute
    )

    raw_event = event.get("raw_event", {})

    event_type = event.get("type")
    player_id = event.get("player_id")

    if event_type == "Starting XI":

        initialise_starting_players(
            raw_event,
            exposure
        )

    elif (
        event_type == "Substitution"
        and player_id is not None
    ):

        player_id = int(player_id)

        if player_id in exposure:
            exposure[player_id]["on_pitch"] = False

        replacement = (
            raw_event
            .get("substitution", {})
            .get("replacement", {})
        )

        replacement_id = replacement.get("id")
        replacement_name = replacement.get("name")

        if replacement_id is not None:
            replacement_id = int(replacement_id)

            exposure[replacement_id] = (
                create_exposure_record(
                    team=event.get("team"),
                    player_name=replacement_name,
                    start_minute=current_minute
                )
            )

    elif (
        event_type == "Player Off"
        and player_id is not None
    ):

        player_id = int(player_id)

        if player_id in exposure:
            exposure[player_id]["on_pitch"] = False

    elif (
        event_type == "Player On"
        and player_id is not None
    ):

        player_id = int(player_id)

        if player_id in exposure:
            exposure[player_id]["on_pitch"] = True

            exposure[player_id][
                "last_update_minute"
            ] = current_minute

        else:
            exposure[player_id] = (
                create_exposure_record(
                    team=event.get("team"),
                    player_name=event.get("player_name"),
                    start_minute=current_minute
                )
            )


def is_progressive_pass(raw_event):
    start = raw_event.get("location")

    pass_data = raw_event.get("pass", {})

    end = pass_data.get("end_location")

    if (
        not isinstance(start, list)
        or not isinstance(end, list)
        or len(start) < 2
        or len(end) < 2
    ):
        return False

    goal_x = 120
    goal_y = 40

    start_distance = math.sqrt(
        (goal_x - start[0]) ** 2
        + (goal_y - start[1]) ** 2
    )

    end_distance = math.sqrt(
        (goal_x - end[0]) ** 2
        + (goal_y - end[1]) ** 2
    )

    if start_distance == 0:
        return False

    reduction = (
        start_distance - end_distance
    ) / start_distance

    return reduction >= 0.25


def create_live_xpass_features(event):
    raw_event = event.get("raw_event")
    freeze_frame = event.get("freeze_frame")

    if not isinstance(raw_event, dict):
        return None

    pass_data = raw_event.get("pass")

    if not isinstance(pass_data, dict):
        return None

    if not isinstance(freeze_frame, list):
        return None

    start_location = raw_event.get("location")

    if (
        not isinstance(start_location, list)
        or len(start_location) < 2
    ):
        return None

    actor = next(
        (
            player
            for player in freeze_frame
            if player.get("actor") is True
        ),
        None
    )

    if actor is None:
        return None

    actor_location = actor.get("location")

    if (
        not isinstance(actor_location, list)
        or len(actor_location) < 2
    ):
        return None

    opponents = [
        player
        for player in freeze_frame
        if (
            player.get("teammate") is False
            and isinstance(
                player.get("location"),
                list
            )
        )
    ]

    teammates = [
        player
        for player in freeze_frame
        if (
            player.get("teammate") is True
            and player.get("actor") is not True
            and isinstance(
                player.get("location"),
                list
            )
        )
    ]

    opponent_distances = [
        math.sqrt(
            (
                player["location"][0]
                - actor_location[0]
            ) ** 2
            +
            (
                player["location"][1]
                - actor_location[1]
            ) ** 2
        )
        for player in opponents
    ]

    teammate_distances = [
        math.sqrt(
            (
                player["location"][0]
                - actor_location[0]
            ) ** 2
            +
            (
                player["location"][1]
                - actor_location[1]
            ) ** 2
        )
        for player in teammates
    ]

    nearest_opponent_distance = (
        min(opponent_distances)
        if opponent_distances
        else None
    )

    nearest_teammate_distance = (
        min(teammate_distances)
        if teammate_distances
        else None
    )

    nearby_opponents_5 = sum(
        distance <= 5
        for distance in opponent_distances
    )

    nearby_teammates_5 = sum(
        distance <= 5
        for distance in teammate_distances
    )

    nearby_opponents_10 = sum(
        distance <= 10
        for distance in opponent_distances
    )

    nearby_teammates_10 = sum(
        distance <= 10
        for distance in teammate_distances
    )

    features = {
        "pass_length":
            pass_data.get("length"),

        "pass_angle_degrees":
            math.degrees(
                pass_data.get("angle", 0)
            ),

        "start_x":
            start_location[0],

        "start_y":
            start_location[1],

        "is_cross":
            int(
                pass_data.get(
                    "cross",
                    False
                )
            ),

        "is_through_ball":
            int(
                pass_data.get(
                    "through_ball",
                    False
                )
            ),

        "is_switch":
            int(
                pass_data.get(
                    "switch",
                    False
                )
            ),

        "nearest_opponent_distance":
            nearest_opponent_distance,

        "nearest_teammate_distance":
            nearest_teammate_distance,

        "under_spatial_pressure":
            int(
                nearest_opponent_distance
                is not None
                and
                nearest_opponent_distance <= 5
            ),

        "nearby_opponents_5":
            nearby_opponents_5,

        "nearby_teammates_5":
            nearby_teammates_5,

        "local_numerical_balance_5":
            nearby_teammates_5
            - nearby_opponents_5,

        "nearby_opponents_10":
            nearby_opponents_10,

        "nearby_teammates_10":
            nearby_teammates_10,

        "local_numerical_balance_10":
            nearby_teammates_10
            - nearby_opponents_10
    }

    return pd.DataFrame(
        [features]
    ).astype(float)


def update_state_metrics(
    state,
    event,
    include_xpass=False
):
    player_id = event.get("player_id")

    if player_id is None:
        return 0

    raw_event = event.get("raw_event", {})
    event_type = event.get("type")

    state["actions"] += 1

    if event_type == "Pass":

        state["pass_attempts"] += 1

        pass_data = raw_event.get("pass", {})

        completed = (
            "outcome" not in pass_data
        )

        if completed:
            state["completed_passes"] += 1

        if is_progressive_pass(raw_event):
            state["progressive_passes"] += 1

        if pass_data.get("shot_assist", False):
            state["shot_assists"] += 1

        if include_xpass:

            xpass_features = (
                create_live_xpass_features(event)
            )

            if xpass_features is not None:

                probability = (
                    xpass_model
                    .predict_proba(
                        xpass_features
                    )[0, 1]
                )

                state[
                    "xpass_evaluated_passes"
                ] += 1

                state[
                    "expected_completions"
                ] += probability

                if completed:
                    state[
                        "xpass_actual_completions"
                    ] += 1

                return 1

    elif event_type == "Shot":

        state["shots"] += 1

        shot_data = raw_event.get("shot", {})

        state["statsbomb_xg"] += (
            shot_data.get(
                "statsbomb_xg",
                0
            )
            or 0
        )

        if (
            shot_data
            .get("outcome", {})
            .get("name")
            == "Goal"
        ):
            state["goals"] += 1

    elif event_type == "Carry":
        state["carries"] += 1

    elif event_type == "Miscontrol":
        state["miscontrols"] += 1

    elif event_type == "Interception":
        state["interceptions"] += 1

    elif event_type == "Ball Recovery":
        state["ball_recoveries"] += 1

    elif event_type == "Dribble":
        state["dribbles"] += 1

    elif event_type == "Duel":
        state["duels"] += 1

    elif event_type == "Pressure":
        state["pressures"] += 1

    return 0


def safe_per90(value, minutes):
    if (
        minutes is None
        or minutes <= 0
    ):
        return np.nan

    return (
        value / minutes
    ) * 90


def safe_rate(numerator, denominator):
    if denominator <= 0:
        return np.nan

    return numerator / denominator


def get_history_value(history, column):
    value = history.get(
        column,
        np.nan
    )

    try:
        return float(value)

    except (TypeError, ValueError):
        return np.nan


def build_halftime_features(
    live_state,
    exposure,
    early_state,
    recent_state
):
    rows = []

    for player_id, state in live_state.items():

        player_exposure = exposure.get(
            player_id
        )

        if player_exposure is None:
            continue

        minutes = player_exposure[
            "minutes_played"
        ]

        if minutes < MIN_FORECAST_MINUTES:
            continue

        early_minutes = player_exposure[
            "early_minutes"
        ]

        recent_minutes = player_exposure[
            "recent_minutes"
        ]

        history = history_lookup.get(
            player_id,
            {}
        )

        row = {
            "player_id":
                player_id,

            "player_name":
                state["player_name"],

            "team":
                state["team"],

            "first_half_minutes":
                minutes
        }

        history_columns = [
            "previous_matches_available",
            "previous_reliable_pass_attempts_per90",
            "previous_reliable_progressive_passes_per90",
            "previous_reliable_carries_per90",
            "previous_reliable_shots_per90",
            "previous_reliable_miscontrols_per90",
            "previous_reliable_shot_assists_per90",
            "last_3_reliable_pass_attempts_per90",
            "last_3_reliable_progressive_passes_per90",
            "last_3_reliable_carries_per90",
            "last_3_reliable_shots_per90",
            "last_3_reliable_miscontrols_per90",
            "last_3_reliable_shot_assists_per90"
        ]

        for column in history_columns:
            row[column] = get_history_value(
                history,
                column
            )

        row[
            "first_half_actions_per90"
        ] = safe_per90(
            state["actions"],
            minutes
        )

        row[
            "first_half_pass_attempts_per90"
        ] = safe_per90(
            state["pass_attempts"],
            minutes
        )

        row[
            "first_half_completed_passes_per90"
        ] = safe_per90(
            state["completed_passes"],
            minutes
        )

        row[
            "first_half_progressive_passes_per90"
        ] = safe_per90(
            state["progressive_passes"],
            minutes
        )

        row[
            "first_half_pass_completion_rate"
        ] = safe_rate(
            state["completed_passes"],
            state["pass_attempts"]
        )

        row[
            "first_half_shots_per90"
        ] = safe_per90(
            state["shots"],
            minutes
        )

        row[
            "first_half_statsbomb_xg_per90"
        ] = safe_per90(
            state["statsbomb_xg"],
            minutes
        )

        row[
            "first_half_carries_per90"
        ] = safe_per90(
            state["carries"],
            minutes
        )

        row[
            "first_half_miscontrols_per90"
        ] = safe_per90(
            state["miscontrols"],
            minutes
        )

        row[
            "first_half_interceptions_per90"
        ] = safe_per90(
            state["interceptions"],
            minutes
        )

        row[
            "first_half_ball_recoveries_per90"
        ] = safe_per90(
            state["ball_recoveries"],
            minutes
        )

        row[
            "first_half_dribbles_per90"
        ] = safe_per90(
            state["dribbles"],
            minutes
        )

        row[
            "first_half_duels_per90"
        ] = safe_per90(
            state["duels"],
            minutes
        )

        row[
            "first_half_pressures_per90"
        ] = safe_per90(
            state["pressures"],
            minutes
        )

        row[
            "first_half_shot_assists_per90"
        ] = safe_per90(
            state["shot_assists"],
            minutes
        )

        evaluated = state[
            "xpass_evaluated_passes"
        ]

        expected = state[
            "expected_completions"
        ]

        actual = state[
            "xpass_actual_completions"
        ]

        if evaluated > 0:

            mean_xpass = (
                expected / evaluated
            )

            actual_rate = (
                actual / evaluated
            )

            row[
                "first_half_mean_xpass"
            ] = mean_xpass

            row[
                "first_half_completions_above_expected"
            ] = (
                actual - expected
            )

            row[
                "first_half_completion_rate_above_expected"
            ] = (
                actual_rate
                - mean_xpass
            )

        else:

            row[
                "first_half_mean_xpass"
            ] = np.nan

            row[
                "first_half_completions_above_expected"
            ] = np.nan

            row[
                "first_half_completion_rate_above_expected"
            ] = np.nan

        early = early_state[player_id]
        recent = recent_state[player_id]

        early_actions = safe_per90(
            early["actions"],
            early_minutes
        )

        recent_actions = safe_per90(
            recent["actions"],
            recent_minutes
        )

        early_progressive = safe_per90(
            early["progressive_passes"],
            early_minutes
        )

        recent_progressive = safe_per90(
            recent["progressive_passes"],
            recent_minutes
        )

        early_carries = safe_per90(
            early["carries"],
            early_minutes
        )

        recent_carries = safe_per90(
            recent["carries"],
            recent_minutes
        )

        early_miscontrols = safe_per90(
            early["miscontrols"],
            early_minutes
        )

        recent_miscontrols = safe_per90(
            recent["miscontrols"],
            recent_minutes
        )

        early_pressures = safe_per90(
            early["pressures"],
            early_minutes
        )

        recent_pressures = safe_per90(
            recent["pressures"],
            recent_minutes
        )

        early_completion = safe_rate(
            early["completed_passes"],
            early["pass_attempts"]
        )

        recent_completion = safe_rate(
            recent["completed_passes"],
            recent["pass_attempts"]
        )

        row[
            "actions_trajectory"
        ] = (
            recent_actions
            - early_actions
        )

        row[
            "progressive_passes_trajectory"
        ] = (
            recent_progressive
            - early_progressive
        )

        row[
            "carries_trajectory"
        ] = (
            recent_carries
            - early_carries
        )

        row[
            "miscontrols_trajectory"
        ] = (
            recent_miscontrols
            - early_miscontrols
        )

        row[
            "pressures_trajectory"
        ] = (
            recent_pressures
            - early_pressures
        )

        row[
            "pass_completion_trajectory"
        ] = (
            recent_completion
            - early_completion
        )

        rows.append(row)

    return pd.DataFrame(rows)


def generate_halftime_forecasts(
    halftime_features
):
    results = halftime_features[
        [
            "player_id",
            "player_name",
            "team",
            "first_half_minutes"
        ]
    ].copy()

    for target, model in (
        forecasting_models.items()
    ):

        required_features = list(
            model.feature_names_in_
        )

        missing = [
            column
            for column in required_features
            if column
            not in halftime_features.columns
        ]

        if missing:
            raise ValueError(
                f"{target} missing features: "
                f"{missing}"
            )

        X = halftime_features[
            required_features
        ].copy()

        for column in X.columns:
            X[column] = pd.to_numeric(
                X[column],
                errors="coerce"
            ).astype(float)

        predictions = model.predict(X)

        results[target] = predictions

    for target in [
        "second_half_actions_per90",
        "second_half_progressive_passes_per90",
        "second_half_pass_completion_rate",
        "second_half_miscontrols_per90",
        "second_half_statsbomb_xg_per90"
    ]:
        results[
            f"raw_{target}"
        ] = results[target]

    results[
        "second_half_actions_per90"
    ] = results[
        "second_half_actions_per90"
    ].clip(lower=0)

    results[
        "second_half_progressive_passes_per90"
    ] = results[
        "second_half_progressive_passes_per90"
    ].clip(lower=0)

    results[
        "second_half_pass_completion_rate"
    ] = results[
        "second_half_pass_completion_rate"
    ].clip(
        lower=0,
        upper=1
    )

    results[
        "second_half_miscontrols_per90"
    ] = results[
        "second_half_miscontrols_per90"
    ].clip(lower=0)

    results[
        "second_half_statsbomb_xg_per90"
    ] = results[
        "second_half_statsbomb_xg_per90"
    ].clip(lower=0)

    return results


def display_halftime_forecasts(forecasts):
    output = forecasts.copy()

    output[
        "Pred Actions/90"
    ] = output[
        "second_half_actions_per90"
    ].round(2)

    output[
        "Pred Progressive/90"
    ] = output[
        "second_half_progressive_passes_per90"
    ].round(2)

    output[
        "Pred Pass Completion %"
    ] = (
        output[
            "second_half_pass_completion_rate"
        ] * 100
    ).round(2)

    output[
        "Pred Miscontrols/90"
    ] = output[
        "second_half_miscontrols_per90"
    ].round(2)

    output[
        "Pred xG/90"
    ] = output[
        "second_half_statsbomb_xg_per90"
    ].round(2)

    output = output[
        [
            "player_name",
            "team",
            "first_half_minutes",
            "Pred Actions/90",
            "Pred Progressive/90",
            "Pred Pass Completion %",
            "Pred Miscontrols/90",
            "Pred xG/90"
        ]
    ]

    output = output.sort_values(
        [
            "team",
            "Pred Actions/90"
        ],
        ascending=[
            True,
            False
        ]
    )

    print()
    print("=" * 90)
    print(
        f"HALFTIME FORECAST — MATCH {MATCH_ID}"
    )
    print("=" * 90)

    print(
        output.to_string(index=False)
    )

    print("=" * 90)


def build_live_assessment(
    live_state,
    exposure
):
    rows = []

    for player_id, state in live_state.items():

        player_exposure = exposure.get(
            player_id
        )

        if player_exposure is None:
            continue

        minutes = player_exposure[
            "minutes_played"
        ]

        if minutes <= 0:
            continue

        history = history_lookup.get(
            player_id,
            {}
        )

        previous_matches = get_history_value(
            history,
            "previous_matches_available"
        )

        if pd.isna(previous_matches):
            previous_matches = 0

        historical_passes = (
            get_history_value(
                history,
                "previous_reliable_pass_attempts_per90"
            )
        )

        historical_progression = (
            get_history_value(
                history,
                "previous_reliable_progressive_passes_per90"
            )
        )

        current_passes = safe_per90(
            state["pass_attempts"],
            minutes
        )

        current_progression = safe_per90(
            state["progressive_passes"],
            minutes
        )

        evaluated = state[
            "xpass_evaluated_passes"
        ]

        expected = state[
            "expected_completions"
        ]

        actual = state[
            "xpass_actual_completions"
        ]

        if evaluated > 0:
            xpass_performance = (
                actual - expected
            )
        else:
            xpass_performance = np.nan

        if state["pass_attempts"] > 0:
            xpass_coverage = (
                evaluated
                / state["pass_attempts"]
            )
        else:
            xpass_coverage = np.nan

        rows.append({
            "player_id":
                player_id,

            "player_name":
                state["player_name"],

            "team":
                state["team"],

            "minutes":
                minutes,

            "previous_matches_available":
                previous_matches,

            "current_pass_attempts_per90":
                current_passes,

            "historical_pass_attempts_per90":
                historical_passes,

            "current_progressive_passes_per90":
                current_progression,

            "historical_progressive_passes_per90":
                historical_progression,

            "xpass_evaluated_passes":
                evaluated,

            "xpass_performance":
                xpass_performance,

            "xpass_coverage":
                xpass_coverage
        })

    return pd.DataFrame(rows)


def generate_live_alerts(assessment_df):
    alerts = []

    if assessment_df.empty:
        return alerts

    for _, row in assessment_df.iterrows():

        player_id = int(
            row["player_id"]
        )

        player_name = row[
            "player_name"
        ]

        team = row["team"]
        minutes = row["minutes"]

        if minutes < 10:
            continue

        xpass_evaluated = row[
            "xpass_evaluated_passes"
        ]

        xpass_performance = row[
            "xpass_performance"
        ]

        xpass_coverage = row[
            "xpass_coverage"
        ]

        if (
            xpass_evaluated >= 5
            and pd.notna(xpass_coverage)
            and xpass_coverage >= 0.80
            and pd.notna(xpass_performance)
        ):

            if xpass_performance <= -2:

                alerts.append({
                    "player_id":
                        player_id,

                    "player_name":
                        player_name,

                    "team":
                        team,

                    "category":
                        "Passing Execution",

                    "severity":
                        "High",

                    "value":
                        xpass_performance,

                    "message":
                        (
                            f"{player_name} is "
                            f"{abs(xpass_performance):.2f} "
                            f"completed passes below "
                            f"contextual expectation."
                        )
                })

            elif xpass_performance <= -1:

                alerts.append({
                    "player_id":
                        player_id,

                    "player_name":
                        player_name,

                    "team":
                        team,

                    "category":
                        "Passing Execution",

                    "severity":
                        "Moderate",

                    "value":
                        xpass_performance,

                    "message":
                        (
                            f"{player_name} is "
                            f"{abs(xpass_performance):.2f} "
                            f"completed passes below "
                            f"contextual expectation."
                        )
                })

        previous_matches = row[
            "previous_matches_available"
        ]

        if previous_matches <= 0:
            continue

        current_passes = row[
            "current_pass_attempts_per90"
        ]

        historical_passes = row[
            "historical_pass_attempts_per90"
        ]

        if (
            pd.notna(current_passes)
            and pd.notna(historical_passes)
            and historical_passes > 0
        ):

            involvement_change = (
                (
                    current_passes
                    - historical_passes
                )
                / historical_passes
            )

            if involvement_change <= -0.40:

                alerts.append({
                    "player_id":
                        player_id,

                    "player_name":
                        player_name,

                    "team":
                        team,

                    "category":
                        "Involvement",

                    "severity":
                        "Moderate",

                    "value":
                        involvement_change,

                    "message":
                        (
                            f"{player_name}'s passing "
                            f"involvement is "
                            f"{abs(involvement_change) * 100:.0f}% "
                            f"below the historical baseline."
                        )
                })

        current_progression = row[
            "current_progressive_passes_per90"
        ]

        historical_progression = row[
            "historical_progressive_passes_per90"
        ]

        if (
            pd.notna(current_progression)
            and pd.notna(historical_progression)
            and historical_progression >= 2
        ):

            progression_change = (
                (
                    current_progression
                    - historical_progression
                )
                / historical_progression
            )

            if progression_change <= -0.50:

                alerts.append({
                    "player_id":
                        player_id,

                    "player_name":
                        player_name,

                    "team":
                        team,

                    "category":
                        "Progression",

                    "severity":
                        "Moderate",

                    "value":
                        progression_change,

                    "message":
                        (
                            f"{player_name}'s progressive "
                            f"passing rate is "
                            f"{abs(progression_change) * 100:.0f}% "
                            f"below the historical baseline."
                        )
                })

    return alerts


def update_alert_persistence(
    current_alerts,
    alert_history,
    checkpoint,
    required_occurrences=2
):
    current_keys = set()
    persistent_alerts = []

    for alert in current_alerts:

        key = (
            alert["player_id"],
            alert["category"]
        )

        current_keys.add(key)

        if key not in alert_history:

            alert_history[key] = {
                "count": 1,
                "alert": alert,
                "last_checkpoint": checkpoint
            }

        else:

            previous_checkpoint = (
                alert_history[key][
                    "last_checkpoint"
                ]
            )

            if previous_checkpoint != checkpoint:
                alert_history[key][
                    "count"
                ] += 1

            alert_history[key][
                "alert"
            ] = alert

            alert_history[key][
                "last_checkpoint"
            ] = checkpoint

        if (
            alert_history[key]["count"]
            >= required_occurrences
        ):

            persistent_alert = alert.copy()

            persistent_alert[
                "persistence"
            ] = alert_history[key]["count"]

            persistent_alert[
                "checkpoint"
            ] = checkpoint

            persistent_alerts.append(
                persistent_alert
            )

    for key in list(
        alert_history.keys()
    ):

        if key not in current_keys:
            del alert_history[key]

    return persistent_alerts


def create_popup_events(
    persistent_alerts,
    popup_registry,
    checkpoint
):
    severity_rank = {
        "Informational": 1,
        "Moderate": 2,
        "High": 3,
        "Critical": 4
    }

    popup_events = []
    active_keys = set()

    for alert in persistent_alerts:

        key = (
            alert["player_id"],
            alert["category"]
        )

        active_keys.add(key)

        severity = alert[
            "severity"
        ]

        previous = popup_registry.get(
            key
        )

        if previous is None:

            popup = alert.copy()

            popup[
                "popup_reason"
            ] = "New persistent alert"

            popup[
                "checkpoint"
            ] = checkpoint

            popup_events.append(
                popup
            )

        elif (
            severity_rank[severity]
            >
            severity_rank[
                previous["severity"]
            ]
        ):

            popup = alert.copy()

            popup[
                "popup_reason"
            ] = "Severity increased"

            popup[
                "checkpoint"
            ] = checkpoint

            popup_events.append(
                popup
            )

        popup_registry[key] = {
            "severity": severity,
            "active": True
        }

    for key in list(
        popup_registry.keys()
    ):

        if key not in active_keys:
            popup_registry[key][
                "active"
            ] = False

    return popup_events


def build_decision_support(
    persistent_alerts,
    forecasts
):
    if forecasts is None or forecasts.empty:
        return pd.DataFrame()

    if not persistent_alerts:
        return pd.DataFrame()

    severity_rank = {
        "Informational": 1,
        "Moderate": 2,
        "High": 3,
        "Critical": 4
    }

    decision_rows = []

    alerts_df = pd.DataFrame(persistent_alerts)

    for player_id, group in alerts_df.groupby("player_id"):
        player_id = int(player_id)

        player_alerts = group.to_dict("records")

        forecast_match = forecasts[
            forecasts["player_id"] == player_id
        ]

        if forecast_match.empty:
            continue

        forecast_row = forecast_match.iloc[0].to_dict()

        ai_result = build_ai_decision(
            player_name=group["player_name"].iloc[0],
            team_name=group["team"].iloc[0],
            alerts=player_alerts,
            forecast=forecast_row
        )

        if ai_result is None:
            continue

        categories = sorted(
            group["category"].dropna().unique().tolist()
        )

        row = {
            "player_id": player_id,
            "player_name": ai_result["player"],
            "team": ai_result["team"],
            "severity": ai_result["severity"],
            "alert_categories": " + ".join(categories),
            "tactical_action": ai_result["tactical_action"],
            "recommendation": ai_result["recommendation"],
            "ai_rule_ids": " + ".join(ai_result["rule_ids"]),
            "reason": ai_result["explanation"],
            "ai_explanation": ai_result["explanation"]
        }

        for column, value in forecast_row.items():
            if column not in row:
                row[column] = value

        decision_rows.append(row)

    if not decision_rows:
        return pd.DataFrame()

    decision_df = pd.DataFrame(decision_rows)

    decision_df["severity_priority"] = (
        decision_df["severity"].map(severity_rank).fillna(0)
    )

    decision_df = (
        decision_df
        .sort_values(
            "severity_priority",
            ascending=False
        )
        .drop(columns=["severity_priority"])
        .reset_index(drop=True)
    )

    return decision_df

def display_decision_support(
    decision_df
):
    print()
    print("=" * 90)
    print(
        "HALFTIME TACTICAL DECISION SUPPORT"
    )
    print("=" * 90)

    if decision_df.empty:
        print(
            "No persistent tactical alerts "
            "active at halftime."
        )
        return

    output = decision_df[
        [
            "player_name",
            "team",
            "severity",
            "alert_categories",
            "recommendation",
            "second_half_pass_completion_rate",
            "second_half_progressive_passes_per90",
            "second_half_miscontrols_per90",
            "second_half_statsbomb_xg_per90"
        ]
    ].copy()

    output[
        "Pred Pass Completion %"
    ] = (
        output[
            "second_half_pass_completion_rate"
        ] * 100
    ).round(2)

    output[
        "Pred Progressive/90"
    ] = output[
        "second_half_progressive_passes_per90"
    ].round(2)

    output[
        "Pred Miscontrols/90"
    ] = output[
        "second_half_miscontrols_per90"
    ].round(2)

    output[
        "Pred xG/90"
    ] = output[
        "second_half_statsbomb_xg_per90"
    ].round(2)

    output = output[
        [
            "player_name",
            "team",
            "severity",
            "alert_categories",
            "recommendation",
            "Pred Pass Completion %",
            "Pred Progressive/90",
            "Pred Miscontrols/90",
            "Pred xG/90"
        ]
    ]

    print(
        output.to_string(index=False)
    )

    print("=" * 90)


live_player_state = defaultdict(
    create_player_state
)

early_state = defaultdict(
    create_segment_state
)

recent_state = defaultdict(
    create_segment_state
)

first_half_exposure = {}


checkpoint_minutes = [
    10,
    15,
    20,
    25,
    30,
    35,
    40,
    45
]

processed_checkpoints = set()

alert_history = {}

popup_registry = {}

active_persistent_alerts = []

all_popup_events = []


consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    group_id=(
        "football-model-inference-alerts-v1"
    )
)


print("Models loaded successfully.")

print(
    f"Historical players available: "
    f"{len(history_lookup)}"
)

print(
    "Waiting for processed football events..."
)


event_count = 0
xpass_prediction_count = 0

halftime_processed = False

halftime_features = None
halftime_forecasts = None
halftime_decisions = None

latest_assessment_df = pd.DataFrame()
latest_popup_events = []
last_period = 1
last_minute = 0
last_second = 0

DASHBOARD_UPDATE_EVERY_EVENTS = 25


def dataframe_records(dataframe):
    if dataframe is None or dataframe.empty:
        return []

    clean = dataframe.copy()
    clean = clean.replace({np.nan: None})

    return clean.to_dict("records")


def write_live_state(
    minute,
    second,
    period,
    match_stage,
    popup_events=None,
    stream_complete=False
):
    write_dashboard_state(
        match_id=MATCH_ID,
        match_minute=minute,
        match_second=second,
        period=period,
        event_count=event_count,
        system_status=(
            "Complete"
            if stream_complete
            else "Active"
        ),
        match_stage=match_stage,
        active_alerts=active_persistent_alerts,
        popup_alerts=(
            popup_events
            if popup_events is not None
            else []
        ),
        player_assessments=dataframe_records(
            latest_assessment_df
        ),
        forecasts=dataframe_records(
            halftime_forecasts
        ),
        decisions=dataframe_records(
            halftime_decisions
        ),
        halftime_complete=halftime_processed,
        stream_complete=stream_complete
    )


write_dashboard_state(
    match_id=MATCH_ID,
    match_minute=0,
    match_second=0,
    period=1,
    event_count=0,
    system_status="Waiting",
    match_stage="Pre-Match",
    active_alerts=[],
    popup_alerts=[],
    player_assessments=[],
    forecasts=[],
    decisions=[],
    halftime_complete=False,
    stream_complete=False
)


for message in consumer:

    event = json.loads(
        message.value.decode("utf-8")
    )

    event_count += 1

    period = event.get("period")

    minute = event.get(
        "minute",
        0
    )

    second = event.get(
        "second",
        0
    )

    current_minute = (
        minute
        + second / 60
    )

    last_period = period
    last_minute = minute
    last_second = second


    if period == 1:

        update_first_half_exposure(
            event,
            first_half_exposure
        )


    player_id = event.get(
        "player_id"
    )


    if player_id is not None:

        player_id = int(player_id)

        state = live_player_state[
            player_id
        ]

        state["team"] = event.get(
            "team"
        )

        state["player_name"] = (
            event.get("player_name")
        )

        xpass_created = (
            update_state_metrics(
                state,
                event,
                include_xpass=True
            )
        )

        xpass_prediction_count += (
            xpass_created
        )


        if period == 1:

            if current_minute < 30:
                segment = early_state[
                    player_id
                ]

            else:
                segment = recent_state[
                    player_id
                ]

            update_state_metrics(
                segment,
                event,
                include_xpass=False
            )


    if period == 1:

        for checkpoint in checkpoint_minutes:

            if (
                current_minute >= checkpoint
                and checkpoint
                not in processed_checkpoints
            ):

                processed_checkpoints.add(
                    checkpoint
                )

                assessment_df = (
                    build_live_assessment(
                        live_player_state,
                        first_half_exposure
                    )
                )

                current_alerts = (
                    generate_live_alerts(
                        assessment_df
                    )
                )

                active_persistent_alerts = (
                    update_alert_persistence(
                        current_alerts,
                        alert_history,
                        checkpoint,
                        required_occurrences=2
                    )
                )

                popup_events = (
                    create_popup_events(
                        active_persistent_alerts,
                        popup_registry,
                        checkpoint
                    )
                )

                all_popup_events.extend(
                    popup_events
                )

                latest_assessment_df = (
                    assessment_df.copy()
                )

                latest_popup_events = (
                    popup_events.copy()
                )

                write_live_state(
                    minute=minute,
                    second=second,
                    period=period,
                    match_stage="First Half",
                    popup_events=popup_events
                )

                print()
                print(
                    f"CHECKPOINT {checkpoint}'"
                )

                print(
                    f"Raw alerts: "
                    f"{len(current_alerts)} | "
                    f"Persistent alerts: "
                    f"{len(active_persistent_alerts)} | "
                    f"New popups: "
                    f"{len(popup_events)}"
                )

                for popup in popup_events:

                    print(
                        f"[{popup['severity']}] "
                        f"{popup['player_name']} | "
                        f"{popup['category']} | "
                        f"{popup['popup_reason']}"
                    )


    if (
        period == 1
        and event.get("type") == "Half End"
        and not halftime_processed
    ):

        halftime_processed = True

        latest_assessment_df = (
            build_live_assessment(
                live_player_state,
                first_half_exposure
            )
        )

        print()
        print(
            f"HALFTIME DETECTED "
            f"AT {minute}:{second:02d}"
        )

        print(
            f"Event index: "
            f"{event.get('index')}"
        )

        halftime_features = (
            build_halftime_features(
                live_player_state,
                first_half_exposure,
                early_state,
                recent_state
            )
        )

        print(
            f"Players eligible for "
            f"forecast: "
            f"{len(halftime_features)}"
        )

        print()
        print(
            "Checking model features..."
        )

        for target, model in (
            forecasting_models.items()
        ):

            required = list(
                model.feature_names_in_
            )

            missing = [
                column
                for column in required
                if column
                not in halftime_features.columns
            ]

            print(
                f"{target}: "
                f"{len(required)} features | "
                f"missing = {len(missing)}"
            )

        halftime_forecasts = (
            generate_halftime_forecasts(
                halftime_features
            )
        )

        display_halftime_forecasts(
            halftime_forecasts
        )

        halftime_decisions = (
            build_decision_support(
                active_persistent_alerts,
                halftime_forecasts
            )
        )

        display_decision_support(
            halftime_decisions
        )

        halftime_features.to_csv(
            "live_halftime_features.csv",
            index=False
        )

        halftime_forecasts.to_csv(
            "live_halftime_forecasts.csv",
            index=False
        )

        if not halftime_decisions.empty:

            halftime_decisions.to_csv(
                "live_halftime_decision_support.csv",
                index=False
            )

        pd.DataFrame(
            all_popup_events
        ).to_csv(
            "live_alert_popups.csv",
            index=False
        )

        print()
        print(
            "Halftime features saved to "
            "live_halftime_features.csv"
        )

        print(
            "Halftime forecasts saved to "
            "live_halftime_forecasts.csv"
        )

        print(
            "Alert popups saved to "
            "live_alert_popups.csv"
        )

        if not halftime_decisions.empty:

            print(
                "Decision support saved to "
                "live_halftime_decision_support.csv"
            )

        write_live_state(
            minute=minute,
            second=second,
            period=period,
            match_stage="Halftime",
            popup_events=[]
        )


    if (
        event_count % DASHBOARD_UPDATE_EVERY_EVENTS
        == 0
    ):

        if period == 1:
            match_stage = "First Half"

        elif period == 2:
            match_stage = "Second Half"

        elif period in [3, 4]:
            match_stage = "Extra Time"

        else:
            match_stage = "Match"

        write_live_state(
            minute=minute,
            second=second,
            period=period,
            match_stage=match_stage,
            popup_events=[]
        )


    if event_count % 500 == 0:

        print(
            f"Processed {event_count} events | "
            f"xPass predictions: "
            f"{xpass_prediction_count} | "
            f"Players tracked: "
            f"{len(live_player_state)}"
        )


    if event_count >= 4160:
        break


consumer.close()


write_live_state(
    minute=last_minute,
    second=last_second,
    period=last_period,
    match_stage="Full Time",
    popup_events=[],
    stream_complete=True
)


print()
print("Full match received.")

print(
    f"Total events processed: "
    f"{event_count}"
)

print(
    f"Players tracked: "
    f"{len(live_player_state)}"
)

print(
    f"xPass predictions made: "
    f"{xpass_prediction_count}"
)

print(
    f"Halftime forecast triggered: "
    f"{halftime_processed}"
)

print(
    f"Popup alerts generated: "
    f"{len(all_popup_events)}"
)


if halftime_forecasts is not None:

    print()
    print(
        "Halftime forecasting pipeline "
        "completed successfully."
    )

    print(
        "Live alert and tactical "
        "decision-support pipeline "
        "completed successfully."
    )

else:

    print()
    print(
        "WARNING: Halftime forecast "
        "was not generated."
    )
    