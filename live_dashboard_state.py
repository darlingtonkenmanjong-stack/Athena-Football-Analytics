import json
import os
import time
import uuid
from pathlib import Path
from datetime import datetime


STATE_FILE = Path("live_dashboard_state.json")


def make_json_safe(value):

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool
        )
    ):
        return value

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set
        )
    ):
        return [
            make_json_safe(item)
            for item in value
        ]

    return str(value)


def write_dashboard_state(
    match_id,
    match_minute,
    match_second=0,
    period=None,
    event_count=0,
    system_status="Active",
    match_stage="First Half",
    active_alerts=None,
    popup_alerts=None,
    player_assessments=None,
    forecasts=None,
    decisions=None,
    halftime_complete=False,
    stream_complete=False
):

    state = {
        "match_id": make_json_safe(match_id),

        "match_minute": make_json_safe(
            match_minute
        ),

        "match_second": make_json_safe(
            match_second
        ),

        "period": make_json_safe(period),

        "event_count": make_json_safe(
            event_count
        ),

        "system_status": system_status,

        "match_stage": match_stage,

        "halftime_complete": bool(
            halftime_complete
        ),

        "stream_complete": bool(
            stream_complete
        ),

        "updated_at": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        ),

        "active_alerts": (
            make_json_safe(active_alerts)
            if active_alerts is not None
            else []
        ),

        "popup_alerts": (
            make_json_safe(popup_alerts)
            if popup_alerts is not None
            else []
        ),

        "player_assessments": (
            make_json_safe(
                player_assessments
            )
            if player_assessments is not None
            else []
        ),

        "forecasts": (
            make_json_safe(forecasts)
            if forecasts is not None
            else []
        ),

        "decisions": (
            make_json_safe(decisions)
            if decisions is not None
            else []
        )
    }

    temporary_file = STATE_FILE.with_name(
        f"{STATE_FILE.stem}_{uuid.uuid4().hex}.tmp"
    )

    try:

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False
            )

            file.flush()

            os.fsync(
                file.fileno()
            )

        max_attempts = 10

        for attempt in range(max_attempts):

            try:

                os.replace(
                    temporary_file,
                    STATE_FILE
                )

                return True

            except PermissionError:

                if attempt == max_attempts - 1:

                    print(
                        "Warning: dashboard state "
                        "file remained locked. "
                        "This update was skipped."
                    )

                    return False

                time.sleep(
                    0.1 * (attempt + 1)
                )

            except OSError as error:

                if attempt == max_attempts - 1:

                    print(
                        "Warning: dashboard state "
                        f"update failed: {error}"
                    )

                    return False

                time.sleep(
                    0.1 * (attempt + 1)
                )

    finally:

        if temporary_file.exists():

            try:
                temporary_file.unlink()

            except OSError:
                pass


def read_dashboard_state():

    if not STATE_FILE.exists():
        return None

    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            with open(
                STATE_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except (
            json.JSONDecodeError,
            PermissionError,
            OSError
        ):

            if attempt < max_attempts - 1:

                time.sleep(0.05)

    return None


if __name__ == "__main__":

    success = write_dashboard_state(
        match_id=3764440,
        match_minute=0,
        match_second=0,
        period=1,
        event_count=0,
        system_status="Ready",
        match_stage="Pre-Match"
    )

    state = read_dashboard_state()

    if success:
        print(
            "Dashboard state created successfully."
        )
    else:
        print(
            "Dashboard state write was skipped."
        )

    print(state)
    