import requests
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

# ── 設定 ──────────────────────────────────────────────────────────────
API_KEY     = os.environ["CWA_API_KEY"]
SENDER      = os.environ["EMAIL_SENDER"]
PASSWORD    = os.environ["EMAIL_PASSWORD"]
RECEIVER    = os.environ["EMAIL_RECEIVER"]
MANUAL_MODE = os.environ.get("MANUAL_MODE", "")

LOCATION    = "大安區"
DATASET_ID  = "F-D0047-061"
BASE_URL    = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
TZ          = timezone(timedelta(hours=8))

# ── 判斷執行模式 ──────────────────────────────────────────────────────
def resolve_mode() -> str:
    if MANUAL_MODE in ("night", "morning"):
        return MANUAL_MODE
    now_hour = datetime.now(TZ).hour
    return "night" if now_hour >= 20 else "morning"

# ── 取得預報資料 ──────────────────────────────────────────────────────
def fetch_forecast() -> dict:
    url = f"{BASE_URL}/{DATASET_ID}"
    params = {
        "Authorization": API_KEY,
        "locationName": LOCATION,
        "elementName": "T,PoP6h",
        "format": "JSON",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# ── 解析並篩選目標日期 08:00–19:00 ───────────────────────────────────
def parse(data: dict, target_date) -> dict:
    # 新版 API 結構：大寫 key
    location = data["records"]["Locations"][0]["Location"][0]
    elements = {e["ElementName"]: e["Time"] for e in location["WeatherElement"]}

    print("取得的氣象元素：", list(elements.keys()))

    results = {"溫度": [], "3小時降雨機率": []}

    for elem_name, time_list in elements.items():
        if elem_name not in results:
            continue
        for slot in time_list:
            # 新版時間 key 是 DataTime
            time_str = slot.get("DataTime") or slot.get("StartTime")
            start = datetime.fromisoformat(time_str).astimezone(TZ)

            if start.date() != target_date:
                continue
            if not (8 <= start.hour <= 19):
                continue

            # 取出數值（key 名稱依元素而異）
            val_dict = slot["ElementValue"][0]
            val = list(val_dict.values())[0]   # 取第一個值，不管 key 叫什麼

            if val in ("", None):
                continue

            results[elem_name].append({
                "time": start.strftime("%H:%M"),
                "value": float(val),
            })

    print(f"氣溫資料筆數：{len(results['溫度'])}")
    print(f"降雨機率資料筆數：{len(results['3小時降雨機率'])}")
    return results

# ── 統計 ──────────────────────────────────────────────────────────────
def stats(values: list) -> dict | None:
    if not values:
        return None
    sorted_v = sorted(values, key=lambda x: x["value"])
    nums = [x["value"] for x in values]
    return {
        "min": sorted_v[0],
        "max": sorted_v[-1],
        "avg": round(sum(nums) / len(nums), 1),
        "len": len(nums),
    }

# ── 組成 Email 內文 ───────────────────────────────────────────────────
def build_body(temp_s: dict, pop_s: dict, target_str: str, mode: str) -> str:
    # label = "隔天" if mode == "night" else "當天"
    lines = [
        "🌡️ 氣溫",
        f"  Max: {temp_s['max']['value']}°C　Time: {temp_s['max']['time']}",
        f"  Min: {temp_s['min']['value']}°C　Time: {temp_s['min']['time']}",
        f"  Avg: {temp_s['avg']}°C",
        "",
        "🌧️ 降雨率",
        f"  Max: {pop_s['max']['value']}%　Time: {pop_s['max']['time']}",
        f"  Min: {pop_s['min']['value']}%　Time: {pop_s['min']['time']}",
        f"  Avg: {pop_s['avg']}%",
        "",
        f"資料筆數：氣溫{temp_s['len']} 筆，降雨率{pop_s['len']}筆。",
        f"預報時地：{target_str}　08:00 – 19:00 台北市大安區",
    ]
    return "\n".join(lines)

# ── 發送 Email ────────────────────────────────────────────────────────
def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart()
    msg["From"]    = SENDER
    msg["To"]      = RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECEIVER, msg.as_string())
    print("✅ Email 已送出。")

# ── 主程式 ────────────────────────────────────────────────────────────
def main():
    mode = resolve_mode()
    now  = datetime.now(TZ)

    target_date = (now + timedelta(days=1)).date() if mode == "night" else now.date()
    target_str  = target_date.strftime("%Y/%m/%d")
    label       = "明日" if mode == "night" else "今日"

    print(f"模式：{mode}　目標日期：{target_str}")

    raw  = fetch_forecast()
    data = parse(raw, target_date)

    temp_s = stats(data["溫度"])
    pop_s  = stats(data["3小時降雨機率"])

    if not temp_s or not pop_s:
        print("⚠️  找不到符合時段的預報資料。")
        return

    body    = build_body(temp_s, pop_s, target_str, mode)
    subject = f"台北大安區{label}（{target_str}）天氣預報"

    print(body)
    send_email(subject, body)

if __name__ == "__main__":
    main()
