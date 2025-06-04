import requests
print("Testing models endpoint...")
try:
    r = requests.get("http://127.0.0.1:8000/models")
    print("Status:", r.status_code)
    if r.status_code == 200:
        print("Models:", r.json())
    else:
        print("Error:", r.text)
except Exception as e:
    print("Exception:", e) 