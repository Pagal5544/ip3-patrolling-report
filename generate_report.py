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
# LOGIN DETAILS
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
    # LOGIN
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

        # -------- Device --------
        raw_device = cols[1].text.strip()
        device = raw_device.replace("RG-PM-CH-HGJ/", "")
        device = device.split("#")[0].replace("RG P", "").strip()
        device = f"P {device}"

        # -------- Other fields --------
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
            last_location,
            False   # late flag
        ])

    # ===============================
    # SORT BY END TIME (OLD → NEW)
    # ===============================
    data.sort(key=lambda x: x[2])

    # ===============================
    # MARK TOP 3 OLDEST
    # ===============================
    for i in range(min(3, len(data))):
        data[i][5] = True

    last_updated = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # ===============================
    # HTML GENERATION
    # ===============================
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

h2 {{
  text-align:center;
  margin-bottom:5px;
}}

.top {{
  text-align:center;
  margin-bottom:15px;
}}

button {{
  padding:6px 14px;
  font-size:14px;
}}

.table-container {{
  display:flex;
  justify-content:center;
}}

table {{
  border-collapse: collapse;
  width:100%;
  max-width:900px;
  background:white;
  position: relative;
  overflow: hidden;
}}

/* ===== WATERMARK ===== */
table::before {{
  content: "शिवा";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-20deg);
  font-size: 140px;
  font-weight: bold;
  color: rgba(0, 0, 0, 0.07);
  white-space: nowrap;
  pointer-events: none;
  z-index: 0;
}}

th, td {{
  border:1px solid #333;
  padding:6px;
  text-align:center;
  font-size:14px;
  position: relative;
  z-index: 1;
}}

th {{
  background:#222;
  color:white;
  cursor:pointer;
}}

/* Device column */
th.device-col, td.device-col {{
  width:70px;
  font-weight:bold;
}}

/* KM Run column */
th.km-col, td.km-col {{
  width:80px;
  font-weight:bold;
  background:#c6efce;
}}

/* Top 3 oldest rows */
tr.late td {{
  background:#c40000 !important;
  color:white;
  font-weight:bold;
}}

footer {{
  margin-top:20px;
  background:yellow;
  padding:12px;
  text-align:center;
  font-size:17px;
  font-weight:bold;
}}
</style>

<script>
let sortAsc = true;

// Numeric sort based on number after P
function sortDevice() {{
  let table = document.getElementById("reportTable");
  let rows = Array.from(table.tBodies[0].rows);

  rows.sort((a, b) => {{
    let A = parseInt(a.cells[0].innerText.replace(/\\D/g,'')) || 0;
    let B = parseInt(b.cells[0].innerText.replace(/\\D/g,'')) || 0;
    return sortAsc ? A - B : B - A;
  }});

  sortAsc = !sortAsc;
  rows.forEach(r => table.tBodies[0].appendChild(r));
}}

function refreshPage() {{
  location.reload();
}}
</script>

</head>
<body>

<h2>Patrolling Report</h2>

<div class="top">
  <div><b>Last Updated:</b> {last_updated}</div><br>
  <button onclick="refreshPage()">🔄 Refresh</button>
</div>

<div class="table-container">
<table id="reportTable">
<thead>
<tr>
  <th class="device-col" onclick="sortDevice()">Device ⬍</th>
  <th>End Time</th>
  <th class="km-col">KM Run</th>
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
</div>

<footer>
लाल रंग से हाइलाइट वाले पेट्रोलमैन अपने GPS रिस्टार्ट (बंद करके दोबारा चालू) कर लें।
</footer>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

finally:
    driver.quit()
