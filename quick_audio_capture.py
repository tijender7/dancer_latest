# Save as quick_audio_capture.py
from selenium import webdriver
import time
import pickle
import os

driver = webdriver.Chrome()

# Load cookies
if os.path.exists("instagram_cookies.pkl"):
    driver.get("https://www.instagram.com")
    time.sleep(3)
    with open("instagram_cookies.pkl", 'rb') as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except:
            pass
    driver.refresh()
    time.sleep(3)

print("📖 Opening saved audio page...")
driver.get("https://www.instagram.com/bold.pooja/saved/audio/")
time.sleep(5)

print("🔧 MANUAL STEPS:")
print("1. Press F12 to open DevTools")
print("2. Go to Network tab")
print("3. Clear the network log")
print("4. Start playing audio tracks")
print("5. Look for .mp3, .m4a files or 'media' requests")
print("6. Copy those URLs")

input("Press ENTER when done...")
driver.quit()