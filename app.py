from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import time
import re
import base64
from io import BytesIO
import requests
from requests import Session
import stat
import subprocess

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

app = Flask(__name__)
CORS(app)

class ZefoyAPI:
    def __init__(self):
        self.driver = None
        self.session = Session()
        self.base_url = "https://zefoy.com"
        self.setup_session()
        
    def setup_session(self):
        """Setup requests session with proper headers"""
        self.session.headers.update({
            'authority': 'zefoy.com',
            'origin': 'https://zefoy.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
            'upgrade-insecure-requests': '1',
        })
        
    def get_chrome_version(self):
        """Get installed Chrome version"""
        try:
            chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
            output = subprocess.check_output([chrome_bin, '--version'], stderr=subprocess.STDOUT)
            version = output.decode('utf-8').strip().split()[-1]
            return version
        except:
            return None
    
    def get_driver(self):
        """Create or return existing WebDriver instance"""
        if self.driver is None:
            self.driver = self._create_driver()
        return self.driver
    
    def _create_driver(self):
        """Create Chrome WebDriver with optimized settings for Render"""
        options = Options()
        
        # Essential Chrome options for headless operation
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-breakpad')
        options.add_argument('--remote-debugging-port=9222')
        
        # Anti-detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('prefs', {
            'profile.default_content_setting_values.notifications': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        })
        
        # Use Chrome from system path
        chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
        if os.path.exists(chrome_bin):
            options.binary_location = chrome_bin
        
        try:
            # Try using system chromedriver first
            chromedriver_path = '/usr/bin/chromedriver'
            if os.path.exists(chromedriver_path):
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
                print("Using system chromedriver")
                return driver
        except Exception as e:
            print(f"System chromedriver failed: {e}")
        
        try:
            # Try with automatic driver management but with proper permissions
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            # Install chromedriver with specific version matching Chrome
            chrome_version = self.get_chrome_version()
            if chrome_version:
                driver_path = ChromeDriverManager(driver_version=chrome_version).install()
            else:
                driver_path = ChromeDriverManager().install()
            
            # Fix permissions
            if driver_path and os.path.exists(driver_path):
                # Make sure it's executable
                st = os.stat(driver_path)
                os.chmod(driver_path, st.st_mode | stat.S_IEXEC)
                
                # If it's a directory, find the actual chromedriver binary
                if os.path.isdir(driver_path):
                    chromedriver_bin = os.path.join(driver_path, 'chromedriver')
                    if os.path.exists(chromedriver_bin):
                        driver_path = chromedriver_bin
                        os.chmod(driver_path, st.st_mode | stat.S_IEXEC)
            
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            print(f"Using webdriver-manager chromedriver at {driver_path}")
            
        except Exception as e:
            print(f"Webdriver-manager failed: {e}")
            # Last resort: try without specifying driver path
            try:
                driver = webdriver.Chrome(options=options)
                print("Using default Chrome driver")
            except Exception as e2:
                print(f"All driver methods failed: {e2}")
                raise
        
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # Execute anti-detection script
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def solve_captcha(self):
        """Solve Zefoy captcha using OCR service"""
        try:
            response = self.session.get(self.base_url, timeout=30)
            source_code = response.text.replace('&amp;', '&')
            
            # Extract captcha token
            captcha_tokens = re.findall(r'<input type="hidden" name="(.*)">', source_code)
            if 'token' in captcha_tokens:
                captcha_tokens.remove('token')
            
            # Get captcha image URL
            captcha_url_match = re.findall(r'img src="([^"]*)"', source_code)
            if not captcha_url_match:
                return {'success': False, 'error': 'No captcha image found'}
            
            captcha_url = captcha_url_match[0]
            
            # Get token answer field name
            token_answer_match = re.findall(r'type="text" name="(.*)" oninput="this.value', source_code)
            if not token_answer_match:
                return {'success': False, 'error': 'No token answer field found'}
            token_answer = token_answer_match[0]
            
            # Download and encode captcha
            img_response = self.session.get(self.base_url + captcha_url, timeout=30)
            encoded_image = base64.b64encode(BytesIO(img_response.content).read()).decode('utf-8')
            
            # Solve using external service
            solve_response = requests.post(
                "https://platipus9999.pythonanywhere.com/",
                json={
                    'captcha': encoded_image,
                    'current_time': datetime.now().strftime("%H:%M:%S")
                },
                timeout=30
            )
            
            if solve_response.status_code != 200:
                return {'success': False, 'error': 'Captcha solving service unavailable'}
            
            captcha_answer = solve_response.json().get("result")
            if not captcha_answer:
                return {'success': False, 'error': 'No captcha answer received'}
            
            time.sleep(1)
            
            # Build POST data
            data = {token_answer: captcha_answer}
            for token_str in captcha_tokens:
                if '" value="' in token_str:
                    token, value = token_str.split('" value="')
                    data[token] = value
            data['token'] = ''
            
            # Submit captcha
            post_response = self.session.post(self.base_url, data=data, timeout=30)
            
            # Check if successful
            if re.findall(r'remove-spaces" name="(.*)" placeholder', post_response.text):
                cookie = self.session.cookies.get('PHPSESSID')
                if cookie:
                    return {
                        'success': True,
                        'cookie': {'name': 'PHPSESSID', 'value': cookie, 'domain': 'zefoy.com'}
                    }
            
            return {'success': False, 'error': 'Captcha verification failed'}
            
        except Exception as e:
            return {'success': False, 'error': f'Captcha solving error: {str(e)}'}
    
    def send_views(self, video_url):
        """Send views to TikTok video - continuous like Zefoy"""
        try:
            driver = self.get_driver()
            
            # Solve captcha and set cookie
            captcha_result = self.solve_captcha()
            if not captcha_result['success']:
                return captcha_result
            
            # Navigate and set cookie
            driver.get(self.base_url)
            driver.add_cookie(captcha_result['cookie'])
            driver.refresh()
            
            wait = WebDriverWait(driver, 15)
            
            # Click views button
            views_button_xpath = "/html/body/div[6]/div/div[2]/div/div/div[5]/div/button"
            views_button = wait.until(EC.element_to_be_clickable((By.XPATH, views_button_xpath)))
            views_button.click()
            
            # Enter video URL
            url_input_xpath = '/html/body/div[10]/div/form/div/input'
            url_input = wait.until(EC.presence_of_element_located((By.XPATH, url_input_xpath)))
            url_input.clear()
            url_input.send_keys(video_url)
            
            # Click search
            search_button_xpath = '/html/body/div[10]/div/form/div/div/button'
            search_button = driver.find_element(By.XPATH, search_button_xpath)
            search_button.click()
            
            time.sleep(3)
            
            # Send views continuously (like original Zefoy)
            sent_count = 0
            
            while True:
                try:
                    # Check rate limit
                    rate_limit_xpath = '//*[@id="c2VuZC9mb2xeb3dlcnNfdGlrdG9V"]/span'
                    try:
                        rate_limit = driver.find_element(By.XPATH, rate_limit_xpath)
                        rate_text = rate_limit.text
                        
                        if "READY" in rate_text:
                            # Click send button
                            send_button_xpath = '/html/body/div[10]/div/div/div[1]/div/form/button'
                            send_button = driver.find_element(By.XPATH, send_button_xpath)
                            send_button.click()
                            sent_count += 1
                            print(f"Sent {sent_count} views")
                            time.sleep(2)
                            
                        elif "seconds" in rate_text:
                            numbers = re.findall(r'(\d+)', rate_text)
                            if numbers:
                                wait_time = int(numbers[0])
                                print(f"Waiting {wait_time} seconds...")
                                time.sleep(wait_time + 2)
                        else:
                            time.sleep(3)
                            
                    except NoSuchElementException:
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"Error in send loop: {e}")
                    time.sleep(5)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        if self.session:
            try:
                self.session.close()
            except:
                pass

# Initialize API instance
zefoy_api = ZefoyAPI()

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'service': 'TikTok View Bot API',
        'status': 'running',
        'endpoint': '/api/views',
        'method': 'POST',
        'body': {'video_url': 'https://www.tiktok.com/@username/video/123456789'}
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
    chrome_exists = os.path.exists(chrome_bin)
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'chrome_installed': chrome_exists
    })

@app.route('/api/views', methods=['POST'])
def api_views():
    """Send views to TikTok video - continuous like Zefoy"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        video_url = data.get('video_url')
        if not video_url:
            return jsonify({'success': False, 'error': 'Missing video_url parameter'}), 400
        
        # Validate TikTok URL
        if not any(domain in video_url.lower() for domain in ['tiktok.com', 'vm.tiktok']):
            return jsonify({'success': False, 'error': 'Invalid TikTok URL'}), 400
        
        # Start sending views (this will run continuously)
        zefoy_api.send_views(video_url)
        
        return jsonify({
            'success': True,
            'message': 'Started sending views',
            'video_url': video_url
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
