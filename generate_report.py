import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ===============================
# LOGIN DETAILS (GitHub Secrets)
# ===============================
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")

if not LOGIN_USERNAME or not LOGIN_PASSWORD:
    raise RuntimeError("LOGIN_USERNAME or LOGIN_PASSWORD missing")


# ===============================
# SELENIUM SETUP
# ===============================
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    # ===============================
    # LOGIN PAGE
    # ===============================
    driver.get("https://ip3.rilapp.com/railways/")

    wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(LOGIN_USERNAME)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(LOGIN_PASSWORD)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()

    time.sleep(8)

    # ===============================
    # REPORT PAGE
    # ===============================
    REPORT_URL = (
        "https://ip3.rilapp.com/railways/patrollingReport.php"
        "?fdate=19/01/2026&ftime=23:00"
        "&tdate=20/01/2026&ttime=07:20"
        "&category=-PM&Submit=Update"
    )

    driver.get(REPORT_URL)

    rows = wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "#example tbody tr")
        )
    )

    data = []

    for r in rows:
        cols = r.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue

        raw_device = cols[1].text.strip()

        device = raw_device.replace("RG-PM-CH-HGJ/", "")
        device = device.split("#")[0]
        device = device.replace("RG P", "").strip()
        device = f"P {device}"

        end_time_full = cols[4].text.strip()
        km_run = cols[6].text.strip()
        last_location = cols[5].text.strip()

        try:
            end_dt = datetime.strptime(end_time_full, "%d/%m/%Y %H:%M:%S")
        except:
            continue

        data.append([
            device,
            end_dt.strftime("%H:%M:%S"),
            end_dt,
            km_run,
            last_location
        ])

    data.sort(key=lambda x: x[2])

    final_rows = [[d[0], d[1], d[3], d[4]] for d in data]

    # ===============================
    # HTML GENERATION
    # ===============================
    html = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Patrolling Report</title>
<style>
body { font-family: Arial; background:#f4f4f4; margin:20px; }
h2 { text-align:center; }
table {
  border-collapse: collapse;
  width: 100%;
  background: white;
}
th, td {
  border: 1px solid #333;
  padding: 8px;
  text-align: center;
}
th {
  background: #222;
  color: white;
}
footer {
  margin-top: 20px;
  background: yellow;
  padding: 15px;
  text-align: center;
  font-size: 20px;
  font-weight: bold;
}
</style>
</head>
<body>

<h2>Patrolling Report</h2>

<table>
<tr>
<th>Device</th>
<th>End Time</th>
<th>KM Run</th>
<th>Last Location</th>
</tr>
"""

    for r in final_rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"

    html += """
</table>

<footer>
लाल रंग से हाइलाइट वाले पेट्रोलमैन अपने GPS रिस्टार्ट (बंद करके दोबारा चालू) कर लें।
</footer>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html generated successfully")

finally:
    driver.quit()
