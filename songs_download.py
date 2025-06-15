import os
import sys
import pickle
import time
import json
import requests
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote
import subprocess
import re
from typing import List, Dict, Optional, Tuple

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

# Additional imports
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    print("Warning: yt-dlp not installed. Install with: pip install yt-dlp")

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: moviepy not installed. Install with: pip install moviepy")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_downloader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class InstagramAudioDownloader:
    """Comprehensive Instagram audio downloader with multiple methods"""
    
    def __init__(self, cookie_path: str = 'D:\\Comfy_UI_V20\\ComfyUI\\output\\dancer\\instagram_cookies.pkl'):
        self.cookie_path = Path(cookie_path)
        self.base_dir = self.cookie_path.parent
        self.download_dir = self.base_dir / 'saved_audio'
        self.temp_dir = self.base_dir / 'temp_downloads'
        self.metadata_file = self.download_dir / 'download_metadata.json'
        
        # Create directories
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize
        self.driver = None
        self.download_history = self.load_metadata()
        self.session = requests.Session()
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
    def load_metadata(self) -> Dict:
        """Load download history metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'downloads': [], 'failed': [], 'last_run': None}
    
    def save_metadata(self):
        """Save download history metadata"""
        self.download_history['last_run'] = datetime.now().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.download_history, f, indent=2)
    
    def setup_driver(self, headless: bool = False) -> webdriver.Chrome:
        """Setup Chrome driver with anti-detection measures"""
        options = webdriver.ChromeOptions()
        
        # Anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Download preferences
        prefs = {
            'download.default_directory': str(self.temp_dir),
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0
        }
        options.add_experimental_option('prefs', prefs)
        
        if headless:
            options.add_argument('--headless=new')
            
        # Additional options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'user-agent={self.user_agents[0]}')
        
        try:
            driver = webdriver.Chrome(options=options)
            
            # Execute anti-detection scripts
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            raise
    
    def load_cookies(self) -> bool:
        """Load cookies from pickle file"""
        if not self.cookie_path.exists():
            logger.warning(f"Cookie file not found at {self.cookie_path}")
            return False
            
        try:
            # Navigate to Instagram first
            self.driver.get('https://www.instagram.com')
            time.sleep(2)
            
            # Load cookies
            with open(self.cookie_path, 'rb') as f:
                cookies = pickle.load(f)
                
            for cookie in cookies:
                # Clean cookie for Selenium
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Failed to add cookie: {e}")
                    
            logger.info("Cookies loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    def save_cookies(self):
        """Save current cookies to pickle file"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookie_path, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_path}")
            
            # Also save as Netscape format for yt-dlp
            self.save_cookies_netscape()
            
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
    
    def save_cookies_netscape(self):
        """Save cookies in Netscape format for yt-dlp"""
        netscape_path = self.cookie_path.with_suffix('.txt')
        try:
            cookies = self.driver.get_cookies()
            with open(netscape_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file was generated by instagram_downloader\n\n")
                
                for cookie in cookies:
                    domain = cookie.get('domain', '')
                    flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie.get('path', '/')
                    secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                    expiry = cookie.get('expiry', 0)
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
                    
            logger.info(f"Netscape cookies saved to {netscape_path}")
            
        except Exception as e:
            logger.error(f"Error saving Netscape cookies: {e}")
    
    def check_login_status(self) -> bool:
        """Check if user is logged in"""
        try:
            # Look for Instagram home icon or profile picture
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, 
                    "//svg[@aria-label='Home' or @aria-label='Inicio'] | //img[contains(@alt, 'profile picture')]"
                ))
            )
            return True
        except TimeoutException:
            return False
    
    def manual_login(self):
        """Handle manual login process"""
        logger.info("Manual login required")
        print("\n" + "="*50)
        print("MANUAL LOGIN REQUIRED")
        print("="*50)
        print("1. Please log in to Instagram in the browser window")
        print("2. Complete any 2FA if required")
        print("3. After successful login, press ENTER here")
        print("="*50)
        
        input("\nPress ENTER after logging in...")
        
        if self.check_login_status():
            self.save_cookies()
            logger.info("Login successful, cookies saved")
        else:
            logger.error("Login verification failed")
            raise Exception("Failed to verify login status")
    
    def navigate_to_saved_audio(self, url: str) -> bool:
        """Navigate to saved audio page with login handling"""
        try:
            # First try with cookies
            if self.load_cookies():
                self.driver.refresh()
                time.sleep(3)
                
                if not self.check_login_status():
                    logger.info("Cookie login failed, manual login required")
                    self.manual_login()
            else:
                # No cookies, need manual login
                self.manual_login()
            
            # Navigate to saved audio page
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            time.sleep(5)
            
            # Check if we can access the page
            if "Login" in self.driver.title or "log in" in self.driver.page_source.lower():
                logger.error("Still not logged in properly")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    def scroll_and_load_all_content(self):
        """Scroll page to load all dynamic content"""
        logger.info("Loading all content by scrolling...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 50  # Prevent infinite scrolling
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Check new height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # Try scrolling up a bit and down again
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check again
                final_height = self.driver.execute_script("return document.body.scrollHeight")
                if final_height == last_height:
                    break
                    
            last_height = new_height
            scroll_attempts += 1
            
            # Log progress
            if scroll_attempts % 5 == 0:
                logger.info(f"Scrolled {scroll_attempts} times...")
    
    def extract_media_data(self) -> List[Dict]:
        """Extract all media URLs and metadata from the page"""
        logger.info("Extracting media data...")
        media_data = []
        
        # JavaScript to extract media information
        js_extract = """
        function extractMediaData() {
            const mediaData = [];
            
            // Find all article elements (posts)
            const articles = document.querySelectorAll('article');
            
            articles.forEach((article, index) => {
                const data = {
                    index: index,
                    type: 'unknown',
                    url: null,
                    thumbnail: null,
                    caption: null,
                    timestamp: new Date().toISOString()
                };
                
                // Try to find video elements
                const video = article.querySelector('video');
                if (video) {
                    data.type = 'video';
                    data.url = video.src || video.currentSrc;
                    
                    // Check for audio track
                    if (video.audioTracks && video.audioTracks.length > 0) {
                        data.hasAudio = true;
                    }
                }
                
                // Try to find audio elements
                const audio = article.querySelector('audio');
                if (audio) {
                    data.type = 'audio';
                    data.url = audio.src || audio.currentSrc;
                }
                
                // Extract thumbnail
                const img = article.querySelector('img');
                if (img) {
                    data.thumbnail = img.src;
                }
                
                // Extract caption
                const caption = article.querySelector('span[data-testid="post-caption-text"]');
                if (caption) {
                    data.caption = caption.textContent;
                }
                
                // Get post link
                const postLink = article.querySelector('a[href*="/p/"]');
                if (postLink) {
                    data.postUrl = postLink.href;
                }
                
                if (data.url || data.postUrl) {
                    mediaData.push(data);
                }
            });
            
            return mediaData;
        }
        
        return extractMediaData();
        """
        
        try:
            extracted_data = self.driver.execute_script(js_extract)
            logger.info(f"Extracted {len(extracted_data)} media items")
            
            # Process and validate data
            for item in extracted_data:
                if item.get('url') or item.get('postUrl'):
                    media_data.append(item)
                    
            return media_data
            
        except Exception as e:
            logger.error(f"Error extracting media data: {e}")
            return []
    
    def download_media_selenium(self, media_item: Dict, index: int) -> Optional[str]:
        """Download media using direct requests"""
        try:
            url = media_item.get('url')
            if not url:
                return None
                
            # Prepare filename
            media_type = media_item.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if media_type == 'video':
                filename = f"instagram_video_{index:04d}_{timestamp}.mp4"
            elif media_type == 'audio':
                filename = f"instagram_audio_{index:04d}_{timestamp}.mp3"
            else:
                filename = f"instagram_media_{index:04d}_{timestamp}.bin"
                
            filepath = self.download_dir / filename
            
            # Download with session
            headers = {
                'User-Agent': self.user_agents[0],
                'Referer': 'https://www.instagram.com/',
            }
            
            response = self.session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            logger.info(f"Downloaded: {filename}")
            
            # Update metadata
            self.download_history['downloads'].append({
                'filename': filename,
                'url': url,
                'type': media_type,
                'timestamp': timestamp,
                'post_url': media_item.get('postUrl'),
                'caption': media_item.get('caption')
            })
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error downloading media {index}: {e}")
            self.download_history['failed'].append({
                'index': index,
                'error': str(e),
                'media_item': media_item
            })
            return None
    
    def download_with_ytdlp(self, url: str, output_dir: Optional[Path] = None) -> Optional[str]:
        """Download media using yt-dlp"""
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp not available")
            return None
            
        output_dir = output_dir or self.download_dir
        cookie_file = self.cookie_path.with_suffix('.txt')
        
        ydl_opts = {
            'outtmpl': str(output_dir / '%(title)s_%(id)s.%(ext)s'),
            'format': 'best[ext=mp4]/best',
            'extract_flat': False,
            'quiet': False,
            'no_warnings': False,
            'cookiefile': str(cookie_file) if cookie_file.exists() else None,
            'user_agent': self.user_agents[0],
            'referer': 'https://www.instagram.com/',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if output_dir == self.download_dir else []
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    # Check for audio extraction
                    audio_file = filename.rsplit('.', 1)[0] + '.mp3'
                    if os.path.exists(audio_file):
                        return audio_file
                    return filename
                    
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            return None
    
    def extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """Extract audio from video file"""
        if not MOVIEPY_AVAILABLE:
            # Try with ffmpeg directly
            return self.extract_audio_ffmpeg(video_path)
            
        try:
            video = VideoFileClip(video_path)
            if video.audio is None:
                logger.warning(f"No audio track in {video_path}")
                return None
                
            audio_path = video_path.rsplit('.', 1)[0] + '.mp3'
            video.audio.write_audiofile(audio_path, bitrate='192k')
            video.close()
            
            logger.info(f"Extracted audio to {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"MoviePy extraction failed: {e}")
            return self.extract_audio_ffmpeg(video_path)
    
    def extract_audio_ffmpeg(self, video_path: str) -> Optional[str]:
        """Extract audio using ffmpeg directly"""
        try:
            audio_path = video_path.rsplit('.', 1)[0] + '.mp3'
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'libmp3lame',
                '-ab', '192k', '-ar', '44100',
                audio_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(audio_path):
                logger.info(f"FFmpeg extracted audio to {audio_path}")
                return audio_path
            else:
                logger.error(f"FFmpeg extraction failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"FFmpeg not available: {e}")
            return None
    
    def process_downloads_for_audio(self):
        """Process all downloads and extract audio"""
        logger.info("Processing downloads for audio extraction...")
        
        video_files = list(self.download_dir.glob("*.mp4"))
        extracted_count = 0
        
        for video_file in video_files:
            audio_file = video_file.with_suffix('.mp3')
            if not audio_file.exists():
                logger.info(f"Extracting audio from {video_file.name}")
                result = self.extract_audio_from_video(str(video_file))
                if result:
                    extracted_count += 1
                    
        logger.info(f"Extracted audio from {extracted_count} videos")
    
    def run_complete_download(self, url: str, method: str = 'auto', max_items: int = None):
        """Run complete download process"""
        logger.info(f"Starting download process with method: {method}")
        
        try:
            # Setup driver
            self.driver = self.setup_driver(headless=False)
            
            # Navigate to saved audio page
            if not self.navigate_to_saved_audio(url):
                raise Exception("Failed to navigate to saved audio page")
            
            # Load all content
            self.scroll_and_load_all_content()
            
            # Extract media data
            media_items = self.extract_media_data()
            
            if not media_items:
                logger.warning("No media items found")
                return
            
            logger.info(f"Found {len(media_items)} media items")
            
            # Limit items if specified
            if max_items:
                media_items = media_items[:max_items]
            
            # Download items
            downloaded = []
            for i, item in enumerate(media_items, 1):
                logger.info(f"Processing item {i}/{len(media_items)}")
                
                # Try different download methods
                filepath = None
                
                if method in ['auto', 'selenium']:
                    filepath = self.download_media_selenium(item, i)
                
                if not filepath and method in ['auto', 'ytdlp'] and item.get('postUrl'):
                    filepath = self.download_with_ytdlp(item['postUrl'])
                    
                if filepath:
                    downloaded.append(filepath)
                    
                # Rate limiting
                time.sleep(2)
                
            logger.info(f"Downloaded {len(downloaded)} items")
            
            # Extract audio from videos
            self.process_downloads_for_audio()
            
            # Save metadata
            self.save_metadata()
            
            # Create summary report
            self.create_summary_report()
            
        except Exception as e:
            logger.error(f"Download process failed: {e}")
            raise
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def create_summary_report(self):
        """Create a summary report of downloads"""
        report_path = self.download_dir / 'download_report.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("Instagram Audio Download Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total downloads: {len(self.download_history['downloads'])}\n")
            f.write(f"Failed downloads: {len(self.download_history['failed'])}\n\n")
            
            f.write("Downloaded Files:\n")
            f.write("-" * 50 + "\n")
            for item in self.download_history['downloads']:
                f.write(f"- {item['filename']}\n")
                if item.get('caption'):
                    f.write(f"  Caption: {item['caption'][:100]}...\n")
                    
            if self.download_history['failed']:
                f.write("\nFailed Downloads:\n")
                f.write("-" * 50 + "\n")
                for item in self.download_history['failed']:
                    f.write(f"- Index: {item['index']}, Error: {item['error']}\n")
                    
        logger.info(f"Summary report saved to {report_path}")


def main():
    """Main execution function"""
    # Configuration
    COOKIE_PATH = r'D:\Comfy_UI_V20\ComfyUI\output\dancer\instagram_cookies.pkl'
    SAVED_AUDIO_URL = 'https://www.instagram.com/bold.pooja/saved/audio/'
    
    # Create downloader instance
    downloader = InstagramAudioDownloader(cookie_path=COOKIE_PATH)
    
    # Run download process
    try:
        downloader.run_complete_download(
            url=SAVED_AUDIO_URL,
            method='auto',  # 'selenium', 'ytdlp', or 'auto'
            max_items=None  # None for all, or specify number
        )
        
        print("\n" + "="*50)
        print("DOWNLOAD COMPLETE!")
        print(f"Files saved to: {downloader.download_dir}")
        print("="*50)
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()