import requests
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

# ── 設定 ──────────────────────────────────────────────────────────────
API_KEY    = os.environ["CWA_API_KEY"]
SENDER     = os.environ["EMAIL_SENDER"]
PASSWORD   = os.environ["EMAIL_PASSWORD"]
RECEIVER   = os.environ["EMAIL_RECEIVER"]
MANUAL_MODE = os.environ.get("MANUAL_MODE", "")   # 手動觸發用

LOCATION   = "大安區"
DATASET_ID = "F-D0047-061"    # 臺北市未來2天逐3小時預報
BASE_URL   = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
TZ         = timezone(timedelta(hours=8))

# ── 判斷執行模式（night / morning）────────────────────────────────────
def resolve_mode() -> str:
    """
    手動觸發時以 MANUAL_MODE 為準。
    自動排程時依台灣當前小時判斷：
      UTC 15:00 → 台灣 23:00 → night
      UTC 23:00 → 台灣 07:00 → morning
    """
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
    location = data["records"]["locations"][0]["location"][0]
    elements = {e["elementName"]: e["time"] for e in location["weatherElement"]}

    results = {"T": [], "PoP6h": []}

    for elem_name, time_list in elements.items():
        if elem_name not in results:
            continue
        for slot in time_list:
            start = datetime.strptime(
                slot["startTime"], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=TZ)

            if start.date() != target_date:
                continue
            if not (8 <= start.hour <= 19):
                continue

            val = slot["elementValue"][0]["value"]
            if val in ("", None):
                continue

            results[elem_name].append({
                "time": start.strftime("%H:%M"),
                "value": float(val),
            })

    return results

# ── 統計：最大、最小、平均 ─────────────────────────────────────────────
def stats(values: list) -> dict | None:
    if not values:
        return None
    sorted_v = sorted(values, key=lambda x: x["value"])
    nums = [x["value"] for x in values]
    return {
        "min": sorted_v[0],
        "max": sorted_v[-1],
        "avg": round(sum(nums) / len(nums), 1),
    }

# ── 組成 Email 內文 ───────────────────────────────────────────────────
def build_body(temp_s: dict, pop_s: dict, target_str: str, mode: str) -> str:
    label = "隔天" if mode == "night" else "當天"
    lines = [
        f"📅 預報日期：{target_str}　｜　地區：台北市大安區",
        f"⏰ 統計區間：08:00 – 19:00（{label}）",
        "",
        "🌡️  氣溫 (°C)",
        f"  最高：{temp_s['max']['value']}°C　時間：{temp_s['max']['time']}",
        f"  最低：{temp_s['min']['value']}°C　時間：{temp_s['min']['time']}",
        f"  平均：{temp_s['avg']}°C",
        "",
        "🌧️  降雨機率 (%)",
        f"  最高：{pop_s['max']['value']}%　時段起：{pop_s['max']['time']}",
        f"  最低：{pop_s['min']['value']}%　時段起：{pop_s['min']['time']}",
        f"  平均：{pop_s['avg']}%",
        "",
        "── 資料來源：中央氣象署開放資料平台 ──",
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

    # 決定查詢目標日期
    target_date = (now + timedelta(days=1)).date() if mode == "night" else now.date()
    target_str  = target_date.strftime("%Y/%m/%d")
    label       = "明日" if mode == "night" else "今日"

    print(f"模式：{mode}　目標日期：{target_str}")

    raw  = fetch_forecast()
    data = parse(raw, target_date)

    if not data["T"] or not data["PoP6h"]:
        print("⚠️  找不到符合時段的預報資料。")
        return

    temp_s = stats(data["T"])
    pop_s  = stats(data["PoP6h"])

    body    = build_body(temp_s, pop_s, target_str, mode)
    subject = f"🌤 台北大安區{label}天氣預報（{target_str}）"

    print(body)
    send_email(subject, body)

if __name__ == "__main__":
    main()
