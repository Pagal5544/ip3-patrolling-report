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

    # ===============================
    # CURRENT TIME (NORMALIZED)
    # ===============================
    now = datetime.strptime(
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "%d/%m/%Y %H:%M:%S"
    )

    data = []

    for r in rows:
        cols = r.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue

        # ---- Device ----
        raw_device = cols[1].text.strip()
        device = raw_device.replace("RG-PM-CH-HGJ/", "")
        device = device.split("#")[0].replace("RG P", "").strip()
        device = f"P {device}"

        # ---- Other fields ----
        end_time_full = cols[4].text.strip()
        km_run = cols[6].text.strip()
        last_location = cols[5].text.strip()

        try:
            end_dt = datetime.strptime(end_time_full, "%d/%m/%Y %H:%M:%S")
        except:
            continue

        delay_seconds = (now - end_dt).total_seconds()
        is_late = delay_seconds >= 600 if delay_seconds >= 0 else False

        data.append([
            device,
            end_dt.strftime("%H:%M:%S"),
            end_dt,
            km_run,
            last_location,
            is_late
        ])

    # ===============================
    # SORT BY END TIME (DEFAULT)
    # ===============================
    data.sort(key=lambda x: x[2])

    # ===============================
    # HTML GENERATION
    # ===============================
    last_updated = now.strftime("%d-%m-%Y %H:%M:%S")

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

.top {{
  text-align:center;
  margin-bottom:15px;
}}

table {{
  border-collapse: collapse;
  width:100%;
  background:white;
}}

th, td {{
  border:1px solid #333;
  padding:8px;
  text-align:center;
}}

th {{
  background:#222;
  color:white;
  cursor:pointer;
}}

tr.late {{
  background:#c40000;
  color:white;
  font-weight:bold;
}}

footer {{
  margin-top:20px;
  background:yellow;
  padding:12px;
  text-align:center;
  font-size:18px;
  font-weight:bold;
}}
</style>

<script>
let sortAsc = true;

// 🔢 Numeric sort based on number after 'P'
function sortDevice() {{
  let table = document.getElementById("reportTable");
  let rows = Array.from(table.tBodies[0].rows);

  rows.sort((a, b) => {{
    let numA = parseInt(a.cells[0].innerText.replace(/\\D/g, "")) || 0;
    let numB = parseInt(b.cells[0].innerText.replace(/\\D/g, "")) || 0;
    return sortAsc ? numA - numB : numB - numA;
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
  <div><b>Last Updated:</b> {last_updated}</div>
  <br>
  <button onclick="refreshPage()">🔄 Refresh</button>
</div>

<table id="reportTable">
<thead>
<tr>
  <th onclick="sortDevice()">Device ⬍</th>
  <th>End Time</th>
  <th>KM Run</th>
  <th>Last Location</th>
</tr>
</thead>
<tbody>
"""

    for d in data:
        row_class = "late" if d[5] else ""
        html += f"""
<tr class="{row_class}">
  <td>{d[0]}</td>
  <td>{d[1]}</td>
  <td>{d[3]}</td>
  <td>{d[4]}</td>
</tr>
"""

    html += """
</tbody>
</table>

<footer>
लाल रंग से हाइलाइट वाले पेट्रोलमैन अपने GPS रिस्टार्ट (बंद करके दोबारा चालू) कर लें।
</footer>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html generated with numeric device sort")

finally:
    driver.quit()
