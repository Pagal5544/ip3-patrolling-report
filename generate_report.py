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
        "?fdate=19/01/2026&ftime=23:00"
        "&tdate=20/01/2026&ttime=07:20"
        "&category=-PM&Submit=Update"
    )
    driver.get(REPORT_URL)

    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#example tbody tr")))

    data = []

    for r in rows:
        cols = r.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue

        raw_device = cols[1].text.strip()
        device = f"P {raw_device.replace('RG-PM-CH-HGJ/','').split('#')[0].replace('RG P','').strip()}"

        end_time_full = cols[4].text.strip()
        km_run = cols[6].text.strip()
        last_location = cols[5].text.strip()

        try:
            end_dt = datetime.strptime(end_time_full, "%d/%m/%Y %H:%M:%S")
        except:
            continue

        data.append([device, end_dt.strftime("%H:%M:%S"), end_dt, km_run, last_location, False])

    data.sort(key=lambda x: x[2])

    # TOP 3 OLDEST
    for i in range(min(3, len(data))):
        data[i][5] = True

    last_updated = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Patrolling Report</title>

<style>
body {{
  font-family: Arial, sans-serif;
  background:#f4f4f4;
  margin:20px;
}}

h2 {{ text-align:center; }}

.top {{ text-align:center; margin-bottom:15px; }}

table {{
  border-collapse: collapse;
  width:100%;
  max-width:900px;
  background:white;
  position:relative;
}}

th, td {{
  border:2px solid #000;
  padding:6px;
  text-align:center;
  font-size:16px;
}}

th {{
  background:#000;
  color:white;
}}

.device-col {{ width:70px; font-weight:bold; }}

.km-col {{
  width:85px;
  font-weight:bold;
  background:#00e600;   /* हमेशा हरा */
  color:#000;
}}

/* 🔴 लाल सिर्फ KM को छोड़कर */
tr.late td:not(.km-col) {{
  background:#ff0000 !important;
  color:white;
  font-weight:bold;
}}

.warning {{
  margin-top:20px;
  background:yellow;
  border:3px solid #000;
  padding:18px;
  text-align:center;
  font-size:26px;
  font-weight:900;
  line-height:1.4;
}}
</style>

</head>
<body>

<h2>Patrolling Report</h2>

<div class="top">
  <div><b>Last Updated:</b> {last_updated}</div>
</div>

<table>
<tr>
  <th class="device-col">Device</th>
  <th>End Time</th>
  <th class="km-col">KM Run</th>
  <th>Last Location</th>
</tr>
"""

    for d in data:
        row_class = "late" if d[5] else ""
        html += f"""
<tr class="{row_class}">
  <td class="device-col">{d[0]}</td>
  <td>{d[1]}</td>
  <td class="km-col">{d[3]}</td>
  <td>{d[4]}</td>
</tr>
"""

    html += f"""
</table>

<div class="warning">
लाल रंग से हाइलाइट वाले पेट्रोलमैन अपने GPS रिस्टार्ट<br>
(बंद करके दोबारा चालू) कर लें।
</div>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

finally:
    driver.quit()
