from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_google_news(location):
    options = Options()
    options.add_argument("--headless")  # Comment this line to see the browser
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # ✅ Correct: wrap ChromeDriverManager in Service
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://news.google.com/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Wait for and access the search bar
        search_input = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "input[aria-label='Search for topics, locations & sources']"
        )))
        search_input.clear()
        search_input.send_keys(location)
        search_input.send_keys(Keys.RETURN)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article h3")))
        headlines = driver.find_elements(By.CSS_SELECTOR, "article h3")

        # print(f"\n📰 Top headlines for {location}:\n{'-'*60}")
        # for i, h in enumerate(headlines[:10], 1):
        #     print(f"{i}. {h.text}")

    except Exception as e:
        print("❌ Exception:", e)
    finally:
        driver.quit()



