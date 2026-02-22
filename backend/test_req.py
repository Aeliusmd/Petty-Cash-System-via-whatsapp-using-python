import urllib.request
from urllib.error import HTTPError, URLError

url = "http://localhost:4101/api/audit-logs/export"
req = urllib.request.Request(url, headers={"ngrok-skip-browser-warning": "true"})
try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Headers:", response.headers)
except HTTPError as e:
    print("HTTP Error:", e.code)
    print("Headers:", e.headers)
    print("Body:", e.read().decode())
except URLError as e:
    print("URL Error:", e.reason)
except Exception as e:
    print("Error:", e)
