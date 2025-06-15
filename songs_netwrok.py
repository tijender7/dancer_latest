import os
import time
import requests
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import pickle
import re
from urllib.parse import urlparse, parse_qs

class InstagramAudioDownloader:
    def __init__(self, cookies_file="instagram_cookies.pkl", download_dir="instagram_audio"):
        self.cookies_file = cookies_file
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.audio_urls = []
        
        # Chrome setup with proper logging
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✅ Chrome started successfully")
    
    def load_cookies(self):
        """Load cookies and verify they work"""
        if os.path.exists(self.cookies_file):
            try:
                print("🍪 Loading saved cookies...")
                
                # Go to Instagram first
                self.driver.get("https://www.instagram.com")
                time.sleep(3)
                
                # Load cookies
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                
                # Clear existing cookies
                self.driver.delete_all_cookies()
                
                # Add each cookie
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        continue
                
                # Refresh to apply cookies
                self.driver.refresh()
                time.sleep(5)
                
                # Check if logged in
                if self.is_logged_in():
                    print("✅ Successfully logged in with saved cookies")
                    return True
                else:
                    print("❌ Saved cookies are expired")
                    return False
                    
            except Exception as e:
                print(f"❌ Error loading cookies: {e}")
                return False
        
        print("📝 No saved cookies found")
        return False
    
    def is_logged_in(self):
        """Check if user is logged in"""
        try:
            # Look for elements that appear when logged in
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            # Multiple checks for login status
            if "login" in current_url:
                return False
                
            if '"viewer":null' in page_source:
                return False
                
            if '"viewer":{"id":' in page_source:
                return True
                
            # Try to find navigation elements
            try:
                self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Home"]')
                return True
            except:
                pass
                
            return "login" not in current_url
            
        except:
            return False
    
    def manual_login(self):
        """Manual login process"""
        print("\n🔐 MANUAL LOGIN REQUIRED")
        print("-" * 40)
        
        self.driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
        
        print("1. Please log in with your Instagram credentials")
        print("2. Complete any 2FA if required")
        print("3. Wait until you reach the Instagram home page")
        print("4. Then come back here and press ENTER")
        
        input("\n⏳ Press ENTER after successful login...")
        
        # Verify login
        if self.is_logged_in():
            print("✅ Login verified successfully")
            self.save_cookies()
            return True
        else:
            print("❌ Login verification failed")
            return False
    
    def save_cookies(self):
        """Save current session cookies"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            print("✅ Cookies saved for future use")
        except Exception as e:
            print(f"❌ Failed to save cookies: {e}")
    
    def extract_audio_from_saved_page(self, saved_audio_url):
        """Extract all audio URLs from the saved audio page"""
        print(f"🎵 Opening saved audio page: {saved_audio_url}")
        
        self.driver.get(saved_audio_url)
        time.sleep(8)  # Wait longer for page load
        
        print("✅ Saved audio page loaded successfully")
        
        # Install comprehensive network interceptor
        print("🔍 Setting up network monitoring...")
        network_script = """
        window.capturedAudioUrls = new Set();
        window.capturedVideoUrls = new Set();
        
        // Override fetch
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const url = typeof args[0] === 'string' ? args[0] : args[0].url;
            
            if (url && (
                url.includes('fbcdn.net') || 
                url.includes('cdninstagram.com') ||
                url.includes('.mp4') || 
                url.includes('.mp3') || 
                url.includes('.m4a')
            )) {
                if (url.includes('video') || url.includes('.mp4')) {
                    window.capturedVideoUrls.add(url);
                } else {
                    window.capturedAudioUrls.add(url);
                }
                console.log('🎵 Captured:', url);
            }
            return originalFetch.apply(this, args);
        };
        
        // Override XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            if (url && (
                url.includes('fbcdn.net') || 
                url.includes('cdninstagram.com') ||
                url.includes('.mp4') || 
                url.includes('.mp3') || 
                url.includes('.m4a')
            )) {
                if (url.includes('video') || url.includes('.mp4')) {
                    window.capturedVideoUrls.add(url);
                } else {
                    window.capturedAudioUrls.add(url);
                }
                console.log('🎵 Captured via XHR:', url);
            }
            return originalOpen.apply(this, arguments);
        };
        """
        
        self.driver.execute_script(network_script)
        
        # Scroll to load content
        print("📜 Scrolling to load all saved audio...")
        for i in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            print(f"📜 Scroll {i+1}/5")
        
        # Find audio reel links - Updated selectors based on debug info
        print("🎯 Finding audio reel links...")
        audio_urls = set()
        
        try:
            # Look for the specific audio reel links we found in debug
            audio_link_selectors = [
                'a[href*="/reels/audio/"]',  # This is the key one from debug!
                'a[href*="/reel/"]',
                'a[href*="/p/"]',
                'a[href*="audio"]'
            ]
            
            all_reel_links = []
            for selector in audio_link_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"🔍 Found {len(links)} links with selector: {selector}")
                    
                    for link in links:
                        href = link.get_attribute('href')
                        if href and self.is_valid_reel_link(href):
                            all_reel_links.append(href)
                            print(f"🎵 Found reel: {href[:80]}...")
                            
                except Exception as e:
                    print(f"⚠️ Selector {selector} failed: {e}")
            
            print(f"🎯 Total unique reel links found: {len(set(all_reel_links))}")
            
            # Visit each reel link to extract audio
            for i, reel_url in enumerate(set(all_reel_links)):
                try:
                    print(f"\n🎵 Processing reel {i+1}/{len(set(all_reel_links))}: {reel_url[:60]}...")
                    
                    # Open reel in new tab
                    self.driver.execute_script("window.open(arguments[0]);", reel_url)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(4)  # Wait for reel to load
                    
                    # Look for audio/video elements
                    try:
                        # Check for audio elements
                        audio_elements = self.driver.find_elements(By.TAG_NAME, "audio")
                        for audio in audio_elements:
                            src = audio.get_attribute("src")
                            if src and self.is_valid_audio_url(src):
                                audio_urls.add(src)
                                print(f"   ✅ Audio: {src[:80]}...")
                        
                        # Check for video elements (Instagram reels often have audio in video)
                        video_elements = self.driver.find_elements(By.TAG_NAME, "video")
                        for video in video_elements:
                            src = video.get_attribute("src")
                            if src and self.is_valid_audio_url(src):
                                audio_urls.add(src)
                                print(f"   ✅ Video with audio: {src[:80]}...")
                        
                        # Get network captured URLs (with error handling)
                        try:
                            captured_audio = self.driver.execute_script("return window.capturedAudioUrls ? Array.from(window.capturedAudioUrls) : [];")
                            captured_video = self.driver.execute_script("return window.capturedVideoUrls ? Array.from(window.capturedVideoUrls) : [];")
                            
                            for url in captured_audio + captured_video:
                                if url and self.is_valid_audio_url(url):
                                    audio_urls.add(url)
                                    print(f"   ✅ Network captured: {url[:80]}...")
                        except Exception as js_error:
                            print(f"   ⚠️ JavaScript capture error (non-critical): {js_error}")
                            # Continue without network capture for this reel
                        
                        # Extract from page source of this reel
                        page_source = self.driver.page_source
                        fbcdn_pattern = r'https://[^"\']*fbcdn\.net[^"\']*\.(mp4|mp3|m4a)[^"\']*'
                        matches = re.findall(fbcdn_pattern, page_source, re.IGNORECASE)
                        
                        for match in matches:
                            url = match[0] if isinstance(match, tuple) else match
                            clean_url = url.replace('\\', '')
                            if self.is_valid_audio_url(clean_url):
                                audio_urls.add(clean_url)
                                print(f"   ✅ Page source: {clean_url[:80]}...")
                        
                    except Exception as e:
                        print(f"   ⚠️ Error extracting from reel: {e}")
                    
                    # Close tab and return to main page
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    
                    # Limit processing to avoid being blocked
                    if i >= 20:  # Process max 20 reels
                        print(f"   🛑 Limiting to first 20 reels to avoid rate limiting")
                        break
                        
                except Exception as e:
                    print(f"   ❌ Error processing reel {i+1}: {e}")
                    # Ensure we're back on main tab
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    continue
        
        except Exception as e:
            print(f"❌ Main extraction failed: {e}")
        
        # Extract from main page source too
        print("\n🔍 Scanning main page source...")
        try:
            page_source = self.driver.page_source
            
            # Look for fbcdn URLs specifically
            fbcdn_patterns = [
                r'https://video-[^"\']*\.fbcdn\.net[^"\']*\.mp4[^"\']*',
                r'https://audio-[^"\']*\.fbcdn\.net[^"\']*\.(mp3|m4a)[^"\']*',
                r'https://[^"\']*\.fbcdn\.net[^"\']*video[^"\']*\.mp4[^"\']*'
            ]
            
            for pattern in fbcdn_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    url = match[0] if isinstance(match, tuple) else match
                    clean_url = url.replace('\\', '').split('"')[0].split("'")[0]
                    if self.is_valid_audio_url(clean_url):
                        audio_urls.add(clean_url)
                        print(f"🎵 Main page source: {clean_url[:80]}...")
        
        except Exception as e:
            print(f"❌ Main page source scan failed: {e}")
        
        final_urls = list(audio_urls)
        print(f"\n🎵 FINAL RESULT: Found {len(final_urls)} valid audio/video URLs")
        
        if final_urls:
            for i, url in enumerate(final_urls[:5]):
                print(f"   {i+1}. {url[:100]}...")
            if len(final_urls) > 5:
                print(f"   ... and {len(final_urls) - 5} more")
        else:
            print("❌ No valid audio URLs found!")
        
        return final_urls
    
    def is_valid_reel_link(self, url):
        """Check if URL is a valid reel link"""
        if not url:
            return False
        
        # Must contain reel or audio indicators
        valid_patterns = [
            '/reels/audio/',
            '/reel/',
            '/p/',
            'audio'
        ]
        
        return any(pattern in url for pattern in valid_patterns) and url.startswith('https://www.instagram.com')
    
    def is_valid_audio_url(self, url):
        """Check if URL is a valid audio/video file URL"""
        if not url or len(url) < 20:
            return False
        
        # Exclude non-media URLs
        exclude_patterns = [
            '/saved/audio/',
            '?hl=',
            '.jpg',
            '.jpeg',
            '.png',
            '.gif',
            '.webp',
            'data:',
            'blob:',
            'javascript:',
            'instagram.com/bold.pooja/saved'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # Include patterns for valid media files
        include_patterns = [
            '.mp4',
            '.mp3',
            '.m4a',
            '.wav',
            '.aac',
            'fbcdn.net',
            'cdninstagram.com',
            'scontent'
        ]
        
        return any(pattern in url.lower() for pattern in include_patterns)
    
    def download_audio_files(self, audio_urls):
        """Download audio files with proper handling of partial content"""
        if not audio_urls:
            print("❌ No audio URLs to download")
            return 0
        
        print(f"\n📥 Starting download of {len(audio_urls)} audio files...")
        
        # Prepare session with cookies
        session = requests.Session()
        
        # Get cookies from browser
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        
        session.cookies.update(cookies)
        
        # Proper headers for Instagram media downloads
        headers = {
            'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
            'Referer': 'https://www.instagram.com/',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not;A=Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        session.headers.update(headers)
        
        success_count = 0
        
        for i, url in enumerate(audio_urls):
            try:
                print(f"\n📥 Downloading {i+1}/{len(audio_urls)}...")
                print(f"🔗 URL: {url[:80]}...")
                
                # First, try a HEAD request to get content info
                try:
                    head_response = session.head(url, timeout=10)
                    content_length = head_response.headers.get('content-length')
                    print(f"📊 Content-Length: {content_length} bytes")
                except:
                    print("⚠️ HEAD request failed, proceeding with GET")
                
                # Make the actual download request
                response = session.get(url, stream=True, timeout=30)
                
                print(f"📡 Response status: {response.status_code}")
                print(f"📋 Response headers: {dict(list(response.headers.items())[:5])}")
                
                if response.status_code in [200, 206]:  # Accept both complete and partial content
                    # Determine file extension and name
                    content_type = response.headers.get('content-type', '')
                    print(f"📄 Content-Type: {content_type}")
                    
                    if 'mp4' in content_type or 'mp4' in url:
                        ext = '.mp4'
                    elif 'm4a' in content_type or 'm4a' in url:
                        ext = '.m4a'
                    elif 'mpeg' in content_type or 'mp3' in url:
                        ext = '.mp3'
                    else:
                        ext = '.mp4'  # Default for Instagram reels
                    
                    filename = f"instagram_audio_{i+1:03d}{ext}"
                    filepath = self.download_dir / filename
                    
                    # Download with progress tracking
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    print(f"💾 Saving to: {filename}")
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                        
                        # Flush and ensure all data is written
                        f.flush()
                        import os
                        os.fsync(f.fileno())
                    
                    # Verify file was created and has content
                    if filepath.exists():
                        file_size = filepath.stat().st_size
                        print(f"✅ File saved: {file_size:,} bytes")
                        
                        if file_size > 1000:  # At least 1KB
                            print(f"✅ Download successful: {filename}")
                            success_count += 1
                        else:
                            print(f"⚠️ File too small ({file_size} bytes), might be incomplete")
                            # Don't delete, might still be valid
                            success_count += 1
                    else:
                        print(f"❌ File was not created: {filename}")
                
                elif response.status_code == 403:
                    print(f"❌ Access forbidden (403) - URL might be expired or protected")
                
                elif response.status_code == 404:
                    print(f"❌ Not found (404) - URL might be invalid")
                
                else:
                    print(f"❌ Unexpected status code: {response.status_code}")
                    print(f"Response text: {response.text[:200]}...")
                
                # Add small delay to avoid rate limiting
                time.sleep(1)
                    
            except requests.exceptions.Timeout:
                print(f"❌ Download timeout for URL {i+1}")
                
            except requests.exceptions.ConnectionError:
                print(f"❌ Connection error for URL {i+1}")
                
            except Exception as e:
                print(f"❌ Unexpected error downloading URL {i+1}: {e}")
                continue
        
        print(f"\n🎉 Download Summary:")
        print(f"   📊 Total URLs: {len(audio_urls)}")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {len(audio_urls) - success_count}")
        print(f"   📁 Saved to: {self.download_dir.absolute()}")
        
        # List downloaded files
        downloaded_files = list(self.download_dir.glob("instagram_audio_*"))
        if downloaded_files:
            print(f"\n📁 Downloaded files:")
            for file in downloaded_files:
                size = file.stat().st_size
                print(f"   {file.name}: {size:,} bytes")
        
        return success_count
    
    def run(self, saved_audio_url="https://www.instagram.com/bold.pooja/saved/audio/"):
        """Main execution flow"""
        print("🚀 INSTAGRAM AUDIO DOWNLOADER - AUTOMATED")
        print("=" * 60)
        
        # Step 1: Handle login
        if self.load_cookies():
            print("✅ Using saved session")
        else:
            print("🔐 Fresh login required")
            if not self.manual_login():
                print("❌ Login failed, exiting...")
                return 0
        
        # Step 2: Extract audio URLs automatically
        audio_urls = self.extract_audio_from_saved_page(saved_audio_url)
        
        if not audio_urls:
            print("❌ No audio URLs found!")
            print("💡 Make sure you have saved audio posts in your account")
            return 0
        
        # Step 3: Download all files
        success_count = self.download_audio_files(audio_urls)
        
        print(f"\n🎉 Process completed! Downloaded {success_count} files")
        return success_count
    
    def __del__(self):
        """Cleanup"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass

# Usage
if __name__ == "__main__":
    try:
        downloader = InstagramAudioDownloader()
        downloader.run("https://www.instagram.com/bold.pooja/saved/audio/")
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()