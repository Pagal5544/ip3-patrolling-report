import os
import time
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")

if not LOGIN_USERNAME or not LOGIN_PASSWORD:
    raise RuntimeError("LOGIN_USERNAME or LOGIN_PASSWORD missing")

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    # LOGIN
    driver.get("https://ip3.rilapp.com/railways/")
    wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(LOGIN_USERNAME)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(LOGIN_PASSWORD)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()
    time.sleep(8)

    # REPORT
    REPORT_URL = (
        "https://ip3.rilapp.com/railways/patrollingReport.php"
        "?fdate=20/01/2026&ftime=23:00"
        "&tdate=21/01/2026&ttime=07:20"
        "&category=-PM&Submit=Update"
    )

    driver.get(REPORT_URL)

    rows = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#example tbody tr"))
    )

    data = []

    for r in rows:
        cols = r.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue

        raw_device = cols[1].text.strip()
        device_num = (
            raw_device
            .replace("RG-PM-CH-HGJ/", "")
            .split("#")[0]
            .replace("RG P", "")
            .strip()
        )
        device = f"P {device_num}"

        end_time_full = cols[4].text.strip()
        km_run = cols[6].text.strip()
        last_location_raw = cols[5].text.strip()

        # Location cleaning
        loc = last_location_raw.upper()
        loc = re.sub(r"OHE\s*HECTO\s*METER\s*POST", "KM ", loc)
        loc = re.sub(r"CENTER\s*LINE\s*OF\s*LC", "फाटक ", loc)
        loc = re.sub(r"CH\s*-\s*ALJN", "", loc)
        loc = re.sub(r"\s+", " ", loc).strip(" -/")
        last_location = loc

        try:
            end_dt = datetime.strptime(end_time_full, "%d/%m/%Y %H:%M:%S")
        except:
            continue

        data.append([device, end_dt.strftime("%H:%M:%S"), end_dt, km_run, last_location, False])

    data.sort(key=lambda x: x[2])

    for i in range(min(3, len(data))):
        data[i][5] = True

    last_updated = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Patrolling Report</title>
</head>
<body>

<h2>राजघाट Night Patrolling Report</h2>
<p><b>Last Updated:</b> {last_updated}</p>
<button onclick="location.reload()">🔄 Refresh</button>

<table border="1" cellspacing="0" cellpadding="6">
<tr>
<th>Device</th>
<th>End Time</th>
<th>KM Run</th>
<th>Last Location</th>
</tr>
"""

    for d in data:
        row_style = ' style="color:red;"' if d[5] else ""
        html += f"""
<tr{row_style}>
<td>{d[0]}</td>
<td>{d[1]}</td>
<td>{d[3]}</td>
<td>{d[4]}</td>
</tr>
"""

    html += """
</table>

<p>
लाल रंग से हाइलाइट पेट्रोलमैन अपने GPS को रिस्टार्ट
(बंद करके दोबारा चालू) कर लें।
</p>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

finally:
    driver.quit()