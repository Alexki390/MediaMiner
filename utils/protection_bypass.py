
"""
Comprehensive protection bypass system for Cloudflare, CAPTCHA, and other restrictions.
"""

import os
import logging
import time
import random
import json
import base64
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudscraper
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from seleniumwire import webdriver as wire_webdriver
from fake_useragent import UserAgent
from PIL import Image
import cv2
import numpy as np
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class ProtectionBypass:
    """Advanced protection bypass system."""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.config = config_manager.get_config() if config_manager else {}
        
        # User agents
        self.ua = UserAgent()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0'
        ]
        
        # Session cache
        self.session_cache = {}
        self.cloudflare_cache = {}
        
    def get_session(self, site_key: str = "default", use_cloudscraper: bool = True) -> requests.Session:
        """Get optimized session for site."""
        if site_key in self.session_cache:
            return self.session_cache[site_key]
            
        if use_cloudscraper:
            session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
        else:
            session = requests.Session()
            
        # Configure session
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        self.session_cache[site_key] = session
        return session
        
    def create_undetected_driver(self, headless: bool = True, use_wire: bool = False) -> Union[uc.Chrome, wire_webdriver.Chrome]:
        """Create undetected Chrome driver."""
        try:
            options = uc.ChromeOptions()
            
            if headless:
                options.add_argument('--headless=new')
                
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--disable-javascript')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            
            # Random viewport
            viewports = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
            width, height = random.choice(viewports)
            options.add_argument(f'--window-size={width},{height}')
            
            # Stealth options
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            }
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            if use_wire:
                # Use selenium-wire for request interception
                seleniumwire_options = {
                    'disable_encoding': True,
                    'suppress_connection_errors': False,
                }
                
                driver = wire_webdriver.Chrome(
                    options=options,
                    seleniumwire_options=seleniumwire_options
                )
            else:
                driver = uc.Chrome(options=options, version_main=None)
                
            # Execute stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            
            return driver
            
        except Exception as e:
            logging.error(f"Failed to create undetected driver: {e}")
            raise
            
    def bypass_cloudflare(self, url: str, timeout: int = 30) -> Optional[str]:
        """Bypass Cloudflare protection."""
        cache_key = urlparse(url).netloc
        
        # Check cache first
        if cache_key in self.cloudflare_cache:
            cached_data = self.cloudflare_cache[cache_key]
            if time.time() - cached_data['timestamp'] < 300:  # 5 minutes
                return cached_data['cookies']
                
        driver = None
        try:
            logging.info(f"Attempting Cloudflare bypass for: {url}")
            
            # Try multiple approaches
            for attempt in range(3):
                try:
                    driver = self.create_undetected_driver(headless=True)
                    driver.get(url)
                    
                    # Wait for Cloudflare challenge to complete
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        page_source = driver.page_source.lower()
                        
                        # Check if still on Cloudflare page
                        cf_indicators = [
                            'checking your browser',
                            'cloudflare',
                            'just a moment',
                            'please wait',
                            'ray id',
                            'security check'
                        ]
                        
                        if not any(indicator in page_source for indicator in cf_indicators):
                            # Successfully bypassed
                            cookies = {}
                            for cookie in driver.get_cookies():
                                cookies[cookie['name']] = cookie['value']
                                
                            # Cache the cookies
                            self.cloudflare_cache[cache_key] = {
                                'cookies': cookies,
                                'timestamp': time.time()
                            }
                            
                            content = driver.page_source
                            driver.quit()
                            return content
                            
                        time.sleep(2)
                        
                    driver.quit()
                    
                except Exception as e:
                    if driver:
                        driver.quit()
                    logging.warning(f"Cloudflare bypass attempt {attempt + 1} failed: {e}")
                    time.sleep(random.uniform(5, 10))
                    
            return None
            
        except Exception as e:
            if driver:
                driver.quit()
            logging.error(f"Cloudflare bypass failed: {e}")
            return None
            
    def solve_captcha(self, image_data: bytes, captcha_type: str = "text") -> Optional[str]:
        """Solve CAPTCHA using image processing."""
        try:
            # Convert bytes to image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if captcha_type == "text":
                return self._solve_text_captcha(img)
            elif captcha_type == "image_selection":
                return self._solve_image_selection_captcha(img)
            else:
                logging.warning(f"Unsupported CAPTCHA type: {captcha_type}")
                return None
                
        except Exception as e:
            logging.error(f"CAPTCHA solving failed: {e}")
            return None
            
    def _solve_text_captcha(self, img: np.ndarray) -> Optional[str]:
        """Solve text-based CAPTCHA."""
        try:
            # Preprocess image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Noise removal
            denoised = cv2.medianBlur(gray, 5)
            
            # Thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Basic OCR (this is a simplified version)
            # In a real implementation, you'd use Tesseract or a CAPTCHA-solving service
            
            # For now, return None to indicate manual intervention needed
            logging.warning("Text CAPTCHA detected - manual intervention may be required")
            return None
            
        except Exception as e:
            logging.error(f"Text CAPTCHA solving failed: {e}")
            return None
            
    def _solve_image_selection_captcha(self, img: np.ndarray) -> Optional[str]:
        """Solve image selection CAPTCHA."""
        try:
            # This would require machine learning models
            # For now, return None to indicate manual intervention needed
            logging.warning("Image selection CAPTCHA detected - manual intervention may be required")
            return None
            
        except Exception as e:
            logging.error(f"Image selection CAPTCHA solving failed: {e}")
            return None
            
    def handle_rate_limiting(self, url: str, delay_base: int = 5) -> None:
        """Handle rate limiting with exponential backoff."""
        domain = urlparse(url).netloc
        
        # Implement per-domain rate limiting
        delay = delay_base + random.uniform(1, 5)
        logging.info(f"Rate limiting for {domain}: waiting {delay:.2f} seconds")
        time.sleep(delay)
        
    def bypass_age_verification(self, driver, url: str) -> bool:
        """Bypass age verification pages."""
        try:
            page_source = driver.page_source.lower()
            
            # Common age verification indicators
            age_indicators = [
                'age verification',
                'are you 18',
                'enter your age',
                'confirm your age',
                'adult content',
                'content warning'
            ]
            
            if any(indicator in page_source for indicator in age_indicators):
                logging.info("Age verification detected, attempting bypass...")
                
                # Try common bypass methods
                bypass_selectors = [
                    "button[onclick*='18']",
                    "button:contains('Yes')",
                    "button:contains('Enter')",
                    "button:contains('Continue')",
                    "input[value='yes' i]",
                    ".age-verify-yes",
                    "#age-yes",
                    ".enter-site"
                ]
                
                for selector in bypass_selectors:
                    try:
                        element = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        element.click()
                        time.sleep(2)
                        return True
                    except:
                        continue
                        
                # Try setting age cookies
                age_cookies = [
                    {'name': 'age_verified', 'value': 'true'},
                    {'name': 'age_gate', 'value': 'passed'},
                    {'name': 'adult', 'value': 'true'},
                    {'name': 'over18', 'value': 'yes'}
                ]
                
                for cookie in age_cookies:
                    driver.add_cookie(cookie)
                    
                driver.refresh()
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Age verification bypass failed: {e}")
            return False
            
    def get_protected_content(self, url: str, retries: int = 3) -> Optional[str]:
        """Get content from protected sites with all bypass methods."""
        
        for attempt in range(retries):
            try:
                logging.info(f"Attempt {attempt + 1} to access protected content: {url}")
                
                # Try simple session first
                session = self.get_session(urlparse(url).netloc, use_cloudscraper=True)
                
                try:
                    response = session.get(url, timeout=30)
                    
                    # Check if content is accessible
                    if response.status_code == 200:
                        content_lower = response.text.lower()
                        
                        # Check for protection indicators
                        protection_indicators = [
                            'cloudflare',
                            'just a moment',
                            'checking your browser',
                            'security check',
                            'access denied',
                            'blocked'
                        ]
                        
                        if not any(indicator in content_lower for indicator in protection_indicators):
                            return response.text
                            
                except Exception:
                    pass
                    
                # If simple session failed, try advanced bypass
                content = self.bypass_cloudflare(url)
                if content:
                    return content
                    
                # Rate limiting between attempts
                if attempt < retries - 1:
                    self.handle_rate_limiting(url, delay_base=10)
                    
            except Exception as e:
                logging.error(f"Protected content access attempt {attempt + 1} failed: {e}")
                
        logging.error(f"Failed to access protected content after {retries} attempts: {url}")
        return None
        
    def extract_media_urls(self, content: str, base_url: str) -> List[str]:
        """Extract media URLs from page content."""
        media_urls = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract image URLs
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    full_url = urljoin(base_url, src)
                    if self._is_valid_media_url(full_url):
                        media_urls.append(full_url)
                        
            # Extract video URLs
            for video in soup.find_all('video'):
                src = video.get('src')
                if src:
                    full_url = urljoin(base_url, src)
                    media_urls.append(full_url)
                    
                # Check source tags
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src:
                        full_url = urljoin(base_url, src)
                        media_urls.append(full_url)
                        
        except Exception as e:
            logging.error(f"Media URL extraction failed: {e}")
            
        return list(set(media_urls))  # Remove duplicates
        
    def _is_valid_media_url(self, url: str) -> bool:
        """Check if URL is a valid media URL."""
        media_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
            '.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv'
        ]
        
        url_lower = url.lower()
        return any(ext in url_lower for ext in media_extensions)
        
    def download_with_protection_bypass(self, url: str, output_path: str) -> bool:
        """Download file with protection bypass."""
        try:
            session = self.get_session(urlparse(url).netloc)
            
            # Add referer to avoid hotlink protection
            headers = {
                'Referer': f"https://{urlparse(url).netloc}/",
                'User-Agent': random.choice(self.user_agents)
            }
            
            response = session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            return True
            
        except Exception as e:
            logging.error(f"Protected download failed: {e}")
            return False
            
    def clear_caches(self):
        """Clear all caches."""
        self.session_cache.clear()
        self.cloudflare_cache.clear()
        logging.info("Protection bypass caches cleared")

# Global instance
protection_bypass = None

def get_protection_bypass(config_manager=None):
    """Get global protection bypass instance."""
    global protection_bypass
    if protection_bypass is None:
        protection_bypass = ProtectionBypass(config_manager)
    return protection_bypass
