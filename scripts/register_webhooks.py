import os
import sys

import requests

API = "https://webexapis.com/v1"
ROOM_TITLES = ("IPA2026", "IPA2026 Exam Room")

def main():
    base = sys.argv[1].rstrip("/")
    target = f"{base}/webhook"
    headers = {"Authorization": f"Bearer {os.environ['WEBEX_BOT_TOKEN']}"}

    rooms = requests.get(f"{API}/rooms", headers=headers, timeout=10).json()["items"]
    room_ids = {r["title"]: r["id"] for r in rooms if r["title"] in ROOM_TITLES}
    missing = set(ROOM_TITLES) - set(room_ids)
    if missing:
        raise SystemExit(f"bot ยังไม่อยู่ในห้อง: {missing}")

    hooks = requests.get(f"{API}/webhooks", headers=headers, timeout=10).json()["items"]
    for hook in hooks:
        requests.delete(f"{API}/webhooks/{hook['id']}", headers=headers, timeout=10)

    for title, room_id in room_ids.items():
        body = {
            "name": f"ipa2026-{title}",
            "targetUrl": target,
            "resource": "messages",
            "event": "created",
            "filter": f"roomId={room_id}",
        }
        r = requests.post(f"{API}/webhooks", headers=headers, json=body, timeout=10)
        r.raise_for_status()
        print("registered:", title)


if __name__ == "__main__":
    main()