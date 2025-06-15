import os
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pickle

class SimpleInstagramDebugger:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script('Object.defineProperty(navigator, \"webdriver\", {get: () => undefined})')
        
    def load_cookies_simple(self):
        cookies_file = 'instagram_cookies.pkl'
        if os.path.exists(cookies_file):
            self.driver.get('https://www.instagram.com')
            time.sleep(3)
            
            with open(cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            
            self.driver.delete_all_cookies()
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    continue
            
            self.driver.refresh()
            time.sleep(5)
            return True
        return False
    
    def debug_page_structure(self, url='https://www.instagram.com/bold.pooja/saved/audio/'):
        print('🔍 DEBUGGING PAGE STRUCTURE')
        print('=' * 50)
        
        print(f'📖 Loading: {url}')
        self.driver.get(url)
        time.sleep(8)
        
        print(f'📍 Current URL: {self.driver.current_url}')
        print(f'📄 Page title: {self.driver.title}')
        
        # Check for different types of elements
        selectors_to_check = [
            ('Article elements', 'article'),
            ('Links with /reel/', 'a[href*=\"/reel/\"]'),
            ('Links with /p/', 'a[href*=\"/p/\"]'),
            ('All links', 'a'),
            ('Buttons', 'button'),
            ('Role=button', '[role=\"button\"]'),
            ('Images', 'img'),
            ('Videos', 'video'),
            ('Audio elements', 'audio')
        ]
        
        for name, selector in selectors_to_check:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f'   {name}: {len(elements)} found')
                
                if selector.startswith('a') and elements:
                    for i, elem in enumerate(elements[:3]):
                        href = elem.get_attribute('href')
                        if href:
                            print(f'      {i+1}. {href[:80]}...')
                
            except Exception as e:
                print(f'   {name}: Error - {e}')
        
        # Save page source
        page_source = self.driver.page_source
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f'💾 Page source saved to debug_page_source.html')
        
        return self.driver.current_url, len(page_source)
    
    def run_debug(self):
        print('🚀 SIMPLE INSTAGRAM DEBUGGER')
        
        if self.load_cookies_simple():
            print('✅ Loaded saved cookies')
        else:
            print('❌ No cookies found - please login manually')
            self.driver.get('https://www.instagram.com/accounts/login/')
            input('Please login and press ENTER...')
        
        current_url, page_size = self.debug_page_structure()
        
        print(f'📊 SUMMARY: URL={current_url}, Size={page_size}')
        input('Press ENTER to close...')
        self.driver.quit()

debugger = SimpleInstagramDebugger()
debugger.run_debug()
