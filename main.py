import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
ALERTS_TABLE = "alerts"
DEALS_TABLE = "deals"

def fetch_secret_flying_deals():
    url = "https://www.secretflying.com/posts/category/business-class-deals/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    posts = soup.select("h2.post-title a")
    deals = []

    for post in posts:
        title = post.text.strip()
        link = post['href']
        if "from" in title.lower():
            parts = title.lower().split("from")[1].split("to")
            if len(parts) >= 2:
                from_city = parts[0].strip().upper()
                to_city = parts[1].split()[0].strip().upper()
                deals.append({
                    "title": title,
                    "link": link,
                    "price": 0,
                    "departure_city": from_city,
                    "arrival_city": to_city,
                    "date": "",
                })
    return deals

def get_alerts():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/{ALERTS_TABLE}",
        headers={
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
        },
    )
    return response.json()

def send_to_supabase(deal):
    deal["created_at"] = datetime.utcnow().isoformat()
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/{DEALS_TABLE}",
        headers={
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json=deal,
    )
    return response.ok

def filter_and_save(deals, alerts):
    matched = 0
    for deal in deals:
        for alert in alerts:
            if (alert['from_airport'] == deal['departure_city']) and (
                alert['to_airport'] == '*' or alert['to_airport'] == deal['arrival_city']
            ):
                print(f"Matching deal found: {deal['title']}")
                send_to_supabase(deal)
                matched += 1
                break
    return matched

@app.route("/run", methods=["GET"])
def run_script():
    print("Fetching deals...")
    deals = fetch_secret_flying_deals()
    print("Checking alerts...")
    alerts = get_alerts()
    print("Filtering and saving...")
    matched = filter_and_save(deals, alerts)
    print("Done.")
    return f"✅ Script executed. {matched} matching deals saved."

if __name__ == "__main__":
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

