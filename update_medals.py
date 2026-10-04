import csv
import json
import random
import time
import zlib
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://back.results.asiangames2026.org/s/AG2026/en/ALL/medals/standings"

# Official Country Name Translation Dictionary
COUNTRY_TRANSLATIONS = {
    "Afghanistan": "阿富汗",
    "Bahrain": "巴林",
    "Bangladesh": "孟加拉国",
    "Bhutan": "不丹",
    "Brunei": "文莱",
    "Brunei Darussalam": "文莱",
    "Cambodia": "柬埔寨",
    "China": "中国",
    "People's Republic of China": "中国",
    "Chinese Taipei": "中华台北",
    "Hong Kong": "香港",
    "Hong Kong, China": "香港",
    "India": "印度",
    "Indonesia": "印度尼西亚",
    "Iran": "伊朗",
    "Islamic Republic of Iran": "伊朗",
    "Iraq": "伊拉克",
    "Japan": "日本",
    "Jordan": "约旦",
    "Kazakhstan": "哈萨克斯坦",
    "North Korea": "朝鲜",
    "DPR Korea": "朝鲜",
    "Democratic People's Republic of Korea": "朝鲜",
    "South Korea": "韩国",
    "Korea": "韩国",
    "Republic of Korea": "韩国",
    "Kuwait": "科威特",
    "Kyrgyzstan": "吉尔吉斯斯坦",
    "Laos": "老挝",
    "Lao PDR": "老挝",
    "Lao People's Democratic Republic": "老挝",
    "Lebanon": "黎巴嫩",
    "Macau": "澳门",
    "Macau, China": "澳门",
    "Macao, China": "澳门",
    "Malaysia": "马来西亚",
    "Maldives": "马尔代夫",
    "Mongolia": "蒙古",
    "Myanmar": "缅甸",
    "Nepal": "尼泊尔",
    "Oman": "阿曼",
    "Pakistan": "巴基斯坦",
    "Palestine": "巴勒斯坦",
    "Philippines": "菲律宾",
    "Qatar": "卡塔尔",
    "Saudi Arabia": "沙特阿拉伯",
    "Singapore": "新加坡",
    "Sri Lanka": "斯里兰卡",
    "Syria": "叙利亚",
    "Syrian Arab Republic": "叙利亚",
    "Tajikistan": "塔吉克斯坦",
    "Thailand": "泰国",
    "East Timor": "东帝汶",
    "Timor-Leste": "东帝汶",
    "Turkmenistan": "土库曼斯坦",
    "United Arab Emirates": "阿联酋",
    "UAE": "阿联酋",
    "Uzbekistan": "乌兹别克斯坦",
    "Vietnam": "越南",
    "Viet Nam": "越南",
    "Yemen": "也门",
}


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


def update_medals_csv():
    time.sleep(random.uniform(1.0, 3.0))
    headers = get_browser_headers()

    try:
        # -------------------------------------------------------------
        # Step 1: Fetch and Decompress API
        # -------------------------------------------------------------
        response = requests.get(
            API_URL, headers=headers, verify=False, timeout=12
        )
        response.raise_for_status()

        try:
            zlib_bytes = response.text.encode("latin-1")
            decompressed_json = zlib.decompress(zlib_bytes).decode("utf-8")
            medals_data = json.loads(decompressed_json)
        except Exception:
            medals_data = response.json()

        if isinstance(medals_data, dict):
            medals_data = medals_data.get("standings", medals_data.get("items", []))

        # Fallback Check: Don't overwrite existing CSV if API payload is empty
        if not medals_data or len(medals_data) == 0:
            print("Fallback Triggered: API returned empty data. Aborting CSV update.")
            return

        # -------------------------------------------------------------
        # Step 2: Parse and Translate Data
        # -------------------------------------------------------------
        processed_list = []

        for item in medals_data:
            counts = item.get("Count", {})
            gold = int(counts.get("ME_GOLD", {}).get("total", 0))
            silver = int(counts.get("ME_SILVER", {}).get("total", 0))
            bronze = int(counts.get("ME_BRONZE", {}).get("total", 0))
            total = int(counts.get("total", {}).get("total", gold + silver + bronze))

            raw_country = item.get("OrgDesc", item.get("Org", "")).strip()
            chinese_name = COUNTRY_TRANSLATIONS.get(raw_country, raw_country)

            is_singapore = raw_country == "新加坡" or raw_country.lower() == "singapore" or item.get("Org") == "SGP"

            # Include only countries with at least 1 medal (or Singapore)
            if total > 0 or is_singapore:
                processed_list.append({
                    "country_en": raw_country,
                    "country_cn": chinese_name,
                    "gold": gold,
                    "silver": silver,
                    "bronze": bronze,
                    "total": total,
                    "is_singapore": is_singapore
                })

        # -------------------------------------------------------------
        # Step 3: Olympic Rank Sorting with Singapore Tie-Breaker
        # -------------------------------------------------------------
        # Sorting priority:
        # 1. Gold, 2. Silver, 3. Bronze, 4. Total
        # 5. Singapore Tie-Breaker: Give Singapore priority (True > False) 
        #    so it lands at the TOP of any tied group!
        processed_list.sort(
            key=lambda x: (
                x["gold"], 
                x["silver"], 
                x["bronze"], 
                x["total"], 
                x["is_singapore"]  # True sorts ahead of False when medals are equal
            ),
            reverse=True
        )

        # Calculate Tied Olympic Ranks (1, 1, 3, 4...)
        ranked_list = []
        current_rank = 1

        for i, item in enumerate(processed_list):
            if i > 0:
                prev = processed_list[i - 1]
                is_tied = (
                    item["gold"] == prev["gold"]
                    and item["silver"] == prev["silver"]
                    and item["bronze"] == prev["bronze"]
                )
                if not is_tied:
                    current_rank = i + 1

            item["rank"] = current_rank
            ranked_list.append(item)

        # -------------------------------------------------------------
        # Step 4: Output Building & Singapore Duplication Logic
        # -------------------------------------------------------------
        final_rows = []
        sg_item = None
        sg_index = -1

        for i, item in enumerate(ranked_list):
            if item["is_singapore"]:
                sg_item = item
                sg_index = i
            
            final_rows.append([
                item["rank"],
                item["country_cn"],
                item["gold"],
                item["silver"],
                item["bronze"],
                item["total"]
            ])

        # Duplicate Singapore at Row 11 ONLY IF:
        # Singapore is ranked STRICTLY OUTSIDE the Top 11 (index > 10, i.e., Rank 12 or below)
        # Since Singapore now wins tie-breakers, if it is tied for Rank 11, it automatically 
        # sits at index 10 (Row 11, bottom of Page 1) as a SINGLE entry!
        if sg_item and sg_index > 10 and sg_item["total"] > 0:
            sg_row = [
                sg_item["rank"],
                sg_item["country_cn"],
                sg_item["gold"],
                sg_item["silver"],
                sg_item["bronze"],
                sg_item["total"]
            ]
            final_rows.insert(10, sg_row)

        # -------------------------------------------------------------
        # Step 5: Write Output to CSV
        # -------------------------------------------------------------
        with open("medals.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # Header with HTML spans
            writer.writerow([
                "#",
                "国家/地区",
                "<span style='color:#000;'>金</span>",
                "<span style='color:#000;'>银</span>",
                "铜",
                "总奖牌"
            ])

            for row in final_rows:
                writer.writerow(row)

        print(f"Successfully updated medals.csv with {len(final_rows)} rows.")

    except Exception as e:
        print(f"Error during execution: {e}. Preserving existing medals.csv.")


if __name__ == "__main__":
    update_medals_csv()
