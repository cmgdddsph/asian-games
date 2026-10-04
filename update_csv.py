import csv
import json
import random
import time
import zlib
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://back.results.asiangames2026.org/s/AG2026/en/ALL/schedule/day/2026-09-16"


def get_browser_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Referer": "https://results.asiangames2026.org/",
        "Origin": "https://results.asiangames2026.org",
    }


def update_csv():
    time.sleep(random.uniform(1.0, 3.0))
    headers = get_browser_headers()

    try:
        response = requests.get(
            API_URL, headers=headers, verify=False, timeout=12
        )
        response.raise_for_status()

        zlib_bytes = response.text.encode("latin-1")
        decompressed_json = zlib.decompress(zlib_bytes).decode("utf-8")
        data = json.loads(decompressed_json)

        schedule = (
            data
            if isinstance(data, list)
            else data.get("schedule", data.get("units", []))
        )

        with open("schedule.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Time",
                "Discipline",
                "Event",
                "Phase / Unit",
                "Status",
                "Venue",
                "Medal",
                "ResCode",
            ])

            for item in schedule:
                writer.writerow([
                    item.get("DateTimeRaw", ""),
                    item.get("DiscDesc", item.get("Disc", "")),
                    item.get("EventDesc", ""),
                    item.get("UnitDesc", item.get("PhaseDesc", "")),
                    item.get("StatusDesc", item.get("Status", "")),
                    item.get("VenueDesc", item.get("Venue", "")),
                    item.get("Medal", ""),
                    item.get("ResCode", ""),
                ])

        print(
            f"Successfully updated schedule.csv with {len(schedule)} items."
        )

    except Exception as e:
        print(f"Error updating CSV: {e}")


if __name__ == "__main__":
    update_csv()
