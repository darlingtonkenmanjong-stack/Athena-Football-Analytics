import json
import time
from datetime import datetime, timezone
from pathlib import Path

from kafka import KafkaProducer


MATCH_ID = 3764440
TOPIC = "football-events"
BOOTSTRAP_SERVERS = "localhost:9092"

EVENTS_PATH = Path(
    f"open-data-master/data/events/{MATCH_ID}.json"
)

THREE_SIXTY_PATH = Path(
    f"open-data-master/data/three-sixty/{MATCH_ID}.json"
)


with open(EVENTS_PATH, "r", encoding="utf-8") as file:
    events = json.load(file)

with open(THREE_SIXTY_PATH, "r", encoding="utf-8") as file:
    three_sixty = json.load(file)


three_sixty_lookup = {
    item["event_uuid"]: item
    for item in three_sixty
}


events = sorted(
    events,
    key=lambda event: event["index"]
)


producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(
        value,
        ensure_ascii=False
    ).encode("utf-8")
)


print(f"Starting replay of match {MATCH_ID}")
print(f"Events: {len(events)}")
print(f"360 records: {len(three_sixty)}")


for event in events:

    event_id = event["id"]

    spatial_data = three_sixty_lookup.get(event_id)

    message = {
        "match_id": MATCH_ID,
        "event_id": event_id,
        "index": event["index"],
        "period": event["period"],
        "timestamp": event["timestamp"],
        "minute": event["minute"],
        "second": event["second"],
        "type": event["type"]["name"],
        "team": event.get("team", {}).get("name"),
        "player_id": event.get("player", {}).get("id"),
        "player_name": event.get("player", {}).get("name"),
        "raw_event": event,
        "freeze_frame": (
            spatial_data.get("freeze_frame")
            if spatial_data
            else None
        ),
        "visible_area": (
            spatial_data.get("visible_area")
            if spatial_data
            else None
        ),
        "sent_at": datetime.now(timezone.utc).isoformat()
    }

    producer.send(
        TOPIC,
        value=message
    )

    print(
        f'{event["index"]} | '
        f'{event["minute"]}:{event["second"]:02d} | '
        f'{event["type"]["name"]} | '
        f'{event.get("player", {}).get("name", "")}'
    )

    time.sleep(0.05)


producer.flush()
producer.close()

print("Match replay complete.")