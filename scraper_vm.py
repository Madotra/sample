import time
import json
import random
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# ------------------------------
# Logging setup
# ------------------------------
LOG_FILE = '/home/flight/sample/scraper_vm.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("Starting scraper script...")

# ------------------------------
# Paths & URLs
# ------------------------------
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "chromedriver")
CHROME_BINARY_PATH = "/usr/bin/google-chrome"

today_date = datetime.now().strftime("%Y%m%d")
URLS = [
    f"https://www.aircanada.com/flifo/search?o=YUL&d=YTZ&t={today_date}&c=ac&l=en",
    f"https://www.aircanada.com/flifo/search?o=YOW&d=YTZ&t={today_date}&c=ac&l=en"
]

# ------------------------------
# Chrome Options
# ------------------------------
options = Options()
options.binary_location = CHROME_BINARY_PATH
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-software-rasterizer")
options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--remote-debugging-port=9222")

# ------------------------------
# Initialize driver
# ------------------------------
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

# ------------------------------
# Helper functions
# ------------------------------
def normalize_status(status):
    if not status:
        return ""
    s = status.lower()
    if "cancelled" in s or "canceled" in s:
        return "cancelled"
    elif "in flight" in s:
        return "in flight"
    elif "left gate" in s:
        return "left gate"
    elif "arrived" in s or "landed" in s:
        return "arrived"
    elif "on time" in s:
        return "on time"
    elif "delayed" in s:
        return "delayed"
    elif "early" in s:
        return "early"
    else:
        return s

def get_flights_data(driver, url):
    flights = []
    try:
        driver.get(url)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ac-card"))
        )
        flight_cards = driver.find_elements(By.CLASS_NAME, "ac-card")
        for card in flight_cards:
            try:
                number_status_div = card.find_element(By.CLASS_NAME, "flight-number-status")
                flight_number = number_status_div.find_element(By.CLASS_NAME, "flight-number").text.strip()
                flight_status = normalize_status(number_status_div.find_element(By.CLASS_NAME, "flight-status").text.strip())

                times_div = card.find_element(By.CLASS_NAME, "flight-times")
                origin_info = times_div.find_element(By.CLASS_NAME, "origin-info")
                origin_time = origin_info.find_element(By.CLASS_NAME, "origin-time").text.strip()
                origin_city = origin_info.find_element(By.CLASS_NAME, "origin-city").text.strip()
                origin_scheduled_time = origin_time

                destination_info = times_div.find_element(By.CLASS_NAME, "destination-info")
                destination_time = destination_info.find_element(By.CLASS_NAME, "destination-time").text.strip()
                destination_city = destination_info.find_element(By.CLASS_NAME, "destination-city").text.strip()
                destination_scheduled_time = destination_time

                if "YTZ" not in destination_city:
                    continue

                flights.append({
                    "flight_number": flight_number,
                    "flight_status": flight_status,
                    "origin_scheduled_time": origin_scheduled_time,
                    "origin_time": origin_time,
                    "origin_city": origin_city,
                    "destination_scheduled_time": destination_scheduled_time,
                    "destination_time": destination_time,
                    "destination_city": destination_city
                })
            except Exception:
                logging.exception("Error parsing a flight card")
                continue
    except Exception:
        logging.exception(f"Error fetching flights from {url}")
    return flights

def get_fin_number(driver, flight_number):
    flight_code = flight_number.replace("AC", "").strip()
    details_url = f"https://www.aircanada.com/flifo/flight-details?f={flight_code}"
    try:
        driver.get(details_url)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fin-number"))
        )
        try:
            detailed_status = driver.find_element(By.CLASS_NAME, "detailed-status").text
            updated_status = normalize_status(detailed_status)
        except:
            updated_status = None

        fin_span = driver.find_element(By.CLASS_NAME, "fin-number")
        return fin_span.text.strip(), updated_status
    except Exception as e:
        logging.error(f"Error fetching FIN number for flight {flight_number}: {e}")
        return None, None

# ------------------------------
# Main scraping logic
# ------------------------------
try:
    all_flights_raw = []
    for url in URLS:
        flights = get_flights_data(driver, url)
        all_flights_raw.extend(flights)

    # Remove duplicates
    seen = set()
    all_flights = []
    for flight in all_flights_raw:
        uid = (flight["flight_number"], flight["origin_time"], flight["destination_time"])
        if uid not in seen:
            seen.add(uid)
            all_flights.append(flight)

    # Fetch FIN numbers safely
    for flight in all_flights:
        try:
            fin_number, updated_status = get_fin_number(driver, flight["flight_number"])
            flight["fin_number"] = fin_number
            if updated_status:
                flight["flight_status"] = updated_status

            # Add live tracking if airborne or left gate
            if flight["flight_status"].lower() in ["in flight", "left gate"]:
                flight_code = flight["flight_number"].replace("AC", "JZA").replace(" ", "")
                flight["live_tracking_link"] = f"https://www.flightradar24.com/{flight_code}"

            time.sleep(random.uniform(1.5, 3.5))

        except Exception:
            logging.exception(f"Unexpected error while updating flight {flight['flight_number']}")
            continue

finally:
    driver.quit()  # Quit only after all flights processed

# ------------------------------
# Next flight calculation
# ------------------------------
now = datetime.now()
next_flight = None
for flight in all_flights:
    try:
        flight_time = datetime.strptime(flight["destination_time"], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if flight_time < now:
            flight_time += timedelta(days=1)  # handle past-midnight flights
        if next_flight is None or flight_time < datetime.strptime(next_flight["destination_time"], "%H:%M").replace(year=now.year, month=now.month, day=now.day):
            next_flight = flight
    except Exception:
        logging.exception(f"Error parsing destination_time for next flight: {flight.get('flight_number', 'N/A')}")

# Sort all flights by destination_time
try:
    all_flights.sort(key=lambda f: datetime.strptime(f["destination_time"], "%H:%M"))
except Exception:
    logging.exception("Error sorting flights by destination_time")

# ------------------------------
# Save to JSON
# ------------------------------
output_data = {
    "last_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_flights": len(all_flights),
    "next_arrival_flight": next_flight,
    "flights": all_flights
}

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flight_data.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

logging.info(f"Flight data saved to {output_path}")
print("Flight data saved to flight_data.json")
