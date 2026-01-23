import os
import time
import re
from datetime import datetime
from datetime import timedelta

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
    driver.get("https://ईp3.rilapp.com/railways/")
    wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(LOGIN_USERNAME)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(LOGIN_PASSWORD)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))).click()
    time.sleep(8)

    # REPORT
    REPORT_URL = (
        "https://ip3.rilapp.com/railways/patrollingReport.php"
        "?fdate=21/01/2026&ftime=23:00"
        "&tdate=22/01/2026&ttime=07:20"
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
        device_num = raw_device.replace("RG-PM-CH-HGJ/", "").split("#")[0].replace("RG P", "").strip()
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

    last_updated = (
    datetime.utcnow() + timedelta(hours=5, minutes=30)
).strftime("%d-%m-%Y %H:%M:%S")

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

.top {{ text-align:center; margin-bottom:12px; }}

.refresh-btn {{
  padding:6px 14px;
  font-size:14px;
}}

table {{
  border-collapse: collapse;
  table-layout: auto;
  width: auto;
  margin: 0 auto;
  background:white;
  position:relative;
}}

table::before {{
  content:"शिवा";
  position:absolute;
  top:50%;
  left:50%;
  transform:translate(-50%,-50%) rotate(-20deg);
  font-size:500px;
  font-weight:900;
  color:rgba(0,0,0,0.07);
  z-index:0;
}}

th, td {{
  border:2px solid #000;
  padding:15px 50px;          /* ⬅️ बड़ा */
  text-align:center;
  font-size:20px;          /* ⬅️ बड़ा */
  font-weight:900;
  white-space: nowrap;
  position:relative;
  z-index:1;
}}

th {{
  background:#D6E6FA;
  color:black;
  cursor:pointer;
}}

.device-col {{ font-weight:bold; }}

.km-col {{
  font-weight:bold;
  background:#00e600;
  color:#000;
}}

tr.late td:not(.km-col) {{
  background:#ff0000 !important;
  color:white;
  font-weight:bold;
}}

.warning {{
  margin-top:16px;
  background:yellow;
  border:3px solid #000;
  padding:15px 5px;              /* ⬅️ छोटा */
  text-align:center;
  font-size:30px;            /* ⬅️ छोटा */
  font-weight:800;
  line-height:1.3;
}}
</style>

<script>
let sortAsc = true;
let sortKmAsc = true;

function sortDevice() {{
  let table = document.getElementById("reportTable");
  let rows = Array.from(table.tBodies[0].rows);

  rows.sort((a, b) => {{
    let A = parseInt(a.cells[0].innerText.replace(/\D/g,'')) || 0;
    let B = parseInt(b.cells[0].innerText.replace(/\D/g,'')) || 0;
    return sortAsc ? A - B : B - A;
  }});

  sortAsc = !sortAsc;
  rows.forEach(r => table.tBodies[0].appendChild(r));
}}

function sortKm() {{
  let table = document.getElementById("reportTable");
  let rows = Array.from(table.tBodies[0].rows);

  rows.sort((a, b) => {{
    let A = parseFloat(a.cells[2].innerText) || 0;
    let B = parseFloat(b.cells[2].innerText) || 0;
    return sortKmAsc ? A - B : B - A;
  }});

  sortKmAsc = !sortKmAsc;
  rows.forEach(r => table.tBodies[0].appendChild(r));
}}

function refreshPage() {{
  location.reload();
}}
</script>

</head>
<body>

<h2>राजघाट Night Patrolling Report</h2>

<div class="top">
  <div><b>Last Updated:</b> {last_updated}</div>
  <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh</button>
</div>

<table id="reportTable">
<thead>
<tr>
  <th class="device-col" onclick="sortDevice()">Device ⬍</th>
  <th>End Time</th>
  <th class="km-col" onclick="sortKm()">KM Run ⬍</th>
  <th>Last Location</th>
</tr>
</thead>
<tbody>
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

    html += """
</tbody>
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
