import time
import json
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pprint import pprint  # For pretty printing the output
import os
from selenium.webdriver.chrome.service import Service

# Set up logging with a timestamp in the log format
logging.basicConfig(
    filename='/home/flight/sample/scraper_vm.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Example of logging with a timestamp
logging.debug("Starting scraper script...")


# Get the absolute path to the chromedriver inside the repo folder
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "chromedriver")
service = Service(executable_path=CHROMEDRIVER_PATH)

# Path to the Chrome binary (Google Chrome for Testing version)
CHROME_BINARY_PATH = "/usr/bin/google-chrome"

# Get today's date in the format YYYYMMDD (e.g., 20250413)
today_date = datetime.now().strftime("%Y%m%d")

# URL 1: Flights from Montreal (YUL) to Toronto Island (YTZ)
url_1 = f"https://www.aircanada.com/flifo/search?o=YUL&d=YTZ&t={today_date}&c=ac&l=en"

# URL 2: Flights from Ottawa (YOW) to Toronto Island (YTZ)
url_2 = f"https://www.aircanada.com/flifo/search?o=YOW&d=YTZ&t={today_date}&c=ac&l=en"

# Set up Chrome options for Selenium to use the custom Chrome binary
options = Options()
options.binary_location = CHROME_BINARY_PATH

# Add headless mode option
# # Add headless mode option
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


# Set up the Chrome WebDriver with the path and options
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)


# Function to extract flight information from a given Air Canada FLIFO URL
def get_flights_data(driver, url):
    driver.get(url)
    # Wait until the flight cards are present on the page
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ac-card"))
    )

    flights = []
    flight_cards = driver.find_elements(By.CLASS_NAME, "ac-card")

    for card in flight_cards:
        try:
            # Extract flight number and status
            number_status_div = card.find_element(By.CLASS_NAME, "flight-number-status")
            flight_number = number_status_div.find_element(By.CLASS_NAME, "flight-number").text.strip()
            flight_status = number_status_div.find_element(By.CLASS_NAME, "flight-status").text.strip()

            # Extract time and city details for origin and destination
            times_div = card.find_element(By.CLASS_NAME, "flight-times")

            origin_info = times_div.find_element(By.CLASS_NAME, "origin-info")
            origin_time = origin_info.find_element(By.CLASS_NAME, "origin-time").text.strip()
            origin_city = origin_info.find_element(By.CLASS_NAME, "origin-city").text.strip()

            # Parse origin scheduled time if present
            if '\n' in origin_city:
                scheduled_time, city = origin_city.split('\n', 1)
                origin_scheduled_time = scheduled_time.replace('Sched. ', '').strip()
                origin_city = city.strip()
            else:
                origin_scheduled_time = None

            destination_info = times_div.find_element(By.CLASS_NAME, "destination-info")
            destination_time = destination_info.find_element(By.CLASS_NAME, "destination-time").text.strip()
            destination_city = destination_info.find_element(By.CLASS_NAME, "destination-city").text.strip()

            # Parse destination scheduled time if present
            if '\n' in destination_city:
                scheduled_time, city = destination_city.split('\n', 1)
                destination_scheduled_time = scheduled_time.replace('Sched. ', '').strip()
                destination_city = city.strip()
            else:
                destination_scheduled_time = None

            # If scheduled times are missing, default them to the actual times
            if origin_scheduled_time is None:
                origin_scheduled_time = origin_time
            if destination_scheduled_time is None:
                destination_scheduled_time = destination_time

            # Filter out non-YTZ destination flights
            if "YTZ" not in destination_city:
                continue

            # Add extracted flight data to list
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

        except Exception as e:
            print(f"Error parsing a flight card: {e}")

    return flights

# Function to fetch the FIN number, update flight status, and optionally add live tracking link
def get_fin_number(driver, flight_number):
    # Remove 'AC' prefix to form correct URL
    flight_code = flight_number.replace("AC", "").strip()
    details_url = f"https://www.aircanada.com/flifo/flight-details?f={flight_code}"
    try:
        # Load the flight details page
        driver.get(details_url)

        # Wait for the FIN number to be available
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "fin-number"))
        )

        # Try to extract the updated flight status from the detailed-status div
        try:
            detailed_status = driver.find_element(By.CLASS_NAME, "detailed-status").text
            if "In flight" in detailed_status:
                updated_status = "In Flight"
            elif "Left gate" in detailed_status:
                updated_status = "Left Gate"
            else:
                updated_status = None
        except:
            updated_status = None

        # Extract and return the FIN number along with possible status update
        fin_span = driver.find_element(By.CLASS_NAME, "fin-number")
        return fin_span.text.strip(), updated_status
    except Exception as e:
        print(f"Error fetching FIN number for flight {flight_number}: {e}")
        return None, None

try:
    # Fetch flights from both URLs
    flights_data_1 = get_flights_data(driver, url_1)
    flights_data_2 = get_flights_data(driver, url_2)

    # Combine and remove duplicate flight entries
    all_flights_raw = flights_data_1 + flights_data_2
    seen = set()
    all_flights = []
    for flight in all_flights_raw:
        uid = (flight["flight_number"], flight["origin_time"], flight["destination_time"])
        if uid not in seen:
            seen.add(uid)
            all_flights.append(flight)

    # Add FIN number, update status, and append live tracking link if applicable
    for flight in all_flights:
        fin_number, updated_status = get_fin_number(driver, flight["flight_number"])
        flight["fin_number"] = fin_number
        if updated_status:
            flight["flight_status"] = updated_status
            # Append flightradar24 live tracking link if flight is airborne or has left gate
            flight_code = flight["flight_number"].replace("AC", "JZA").replace(" ", "")
            flight["live_tracking_link"] = f"https://www.flightradar24.com/{flight_code}"
        time.sleep(random.uniform(1.5, 3.5))  # Delay to prevent rate-limiting or blocking

finally:
    # Close the browser instance
    driver.quit()

# Identify the next arriving flight based on destination time
now = datetime.now()
next_flight = None
for flight in all_flights:
    try:
        flight_time = datetime.strptime(flight["destination_time"], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if flight_time >= now:
            if next_flight is None or flight_time < datetime.strptime(next_flight["destination_time"], "%H:%M").replace(year=now.year, month=now.month, day=now.day):
                next_flight = flight
    except Exception as e:
        print(f"Error parsing destination_time for next flight comparison: {e}")

# Sort all flights by destination_time for easier chronological view
try:
    all_flights.sort(key=lambda f: datetime.strptime(f["destination_time"], "%H:%M"))
except Exception as e:
    print(f"Error sorting flights by destination_time: {e}")

# Prepare output data
output_data = {
    "last_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_flights": len(all_flights),
    "next_arrival_flight": next_flight,
    "flights": all_flights
}

# Save the flight data to a JSON file
with open("flight_data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

print("Flight data saved to flight_data.json")
