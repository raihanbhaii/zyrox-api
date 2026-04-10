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
import threading

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
        self.is_sending = False
        self.setup_session()
       
    def setup_session(self):
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
        try:
            chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
            output = subprocess.check_output([chrome_bin, '--version'], stderr=subprocess.STDOUT)
            version = output.decode('utf-8').strip().split()[-1]
            return version
        except:
            return None
   
    def get_driver(self):
        if self.driver is None:
            self.driver = self._create_driver()
        return self.driver
   
    def _create_driver(self):
        options = Options()
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
        options.add_argument('--no-first-run')
        options.add_argument('--disable-breakpad')
        options.add_argument('--remote-debugging-port=9222')
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
        if os.path.exists(chrome_bin):
            options.binary_location = chrome_bin
       
        try:
            chromedriver_path = '/usr/bin/chromedriver'
            if os.path.exists(chromedriver_path):
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
                print("✅ Using system chromedriver")
                return driver
        except Exception as e:
            print(f"System chromedriver failed: {e}")
       
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            chrome_version = self.get_chrome_version()
            driver_path = ChromeDriverManager(driver_version=chrome_version).install() if chrome_version else ChromeDriverManager().install()
            
            if os.path.exists(driver_path):
                st = os.stat(driver_path)
                os.chmod(driver_path, st.st_mode | stat.S_IEXEC)
            
            service = Service(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            print("✅ Using webdriver-manager chromedriver")
        except Exception as e:
            print(f"Webdriver-manager failed: {e}")
            driver = webdriver.Chrome(options=options)
            print("✅ Using default Chrome driver")
       
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
   
    def solve_captcha(self):
        try:
            response = self.session.get(self.base_url, timeout=30)
            source = response.text.replace('&amp;', '&')
           
            captcha_url_match = re.findall(r'img src="([^"]*)"', source)
            if not captcha_url_match:
                return {'success': False, 'error': 'No captcha image found'}
           
            token_answer_match = re.findall(r'type="text" name="(.*)" oninput="this.value', source)
            if not token_answer_match:
                return {'success': False, 'error': 'No token answer field found'}
            
            token_answer = token_answer_match[0]
            img_response = self.session.get(self.base_url + captcha_url_match[0], timeout=30)
            encoded_image = base64.b64encode(img_response.content).decode('utf-8')
           
            solve_response = requests.post(
                "https://platipus9999.pythonanywhere.com/",
                json={'captcha': encoded_image, 'current_time': datetime.now().strftime("%H:%M:%S")},
                timeout=30
            )
           
            captcha_answer = solve_response.json().get("result")
            if not captcha_answer:
                return {'success': False, 'error': 'Captcha solving failed'}
           
            # Better hidden fields parsing
            hidden = re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"(?:[^>]+value="([^"]*)")?', source)
            data = {name: value or '' for name, value in hidden}
            data[token_answer] = captcha_answer
            data['token'] = ''
           
            post_response = self.session.post(self.base_url, data=data, timeout=30)
           
            if re.search(r'remove-spaces" name=', post_response.text):
                cookie = self.session.cookies.get('PHPSESSID')
                if cookie:
                    return {
                        'success': True,
                        'cookie': {'name': 'PHPSESSID', 'value': cookie, 'domain': 'zefoy.com'}
                    }
           
            return {'success': False, 'error': 'Captcha verification failed'}
           
        except Exception as e:
            return {'success': False, 'error': f'Captcha error: {str(e)}'}
   
    def send_views(self, video_url):
        self.is_sending = True
        try:
            driver = self.get_driver()
            captcha_result = self.solve_captcha()
            if not captcha_result['success']:
                self.is_sending = False
                print("❌ Captcha failed:", captcha_result['error'])
                return

            driver.get(self.base_url)
            driver.add_cookie(captcha_result['cookie'])
            driver.refresh()

            wait = WebDriverWait(driver, 15)
            
            # Click Views button
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div/div[2]/div/div/div[5]/div/button"))).click()
            
            # Enter URL
            url_input = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[10]/div/form/div/input')))
            url_input.clear()
            url_input.send_keys(video_url)
            
            # Search
            driver.find_element(By.XPATH, '/html/body/div[10]/div/form/div/div/button').click()
            time.sleep(3)

            sent_count = 0
            while True:
                try:
                    rate_text = driver.find_element(By.XPATH, '//*[@id="c2VuZC9mb2xeb3dlcnNfdGlrdG9V"]/span').text
                    
                    if "READY" in rate_text.upper():
                        driver.find_element(By.XPATH, '/html/body/div[10]/div/div/div[1]/div/form/button').click()
                        sent_count += 1
                        print(f"✅ Sent {sent_count} views")
                        time.sleep(2)
                    elif "seconds" in rate_text.lower():
                        wait_time = int(re.findall(r'(\d+)', rate_text)[0])
                        print(f"⏳ Waiting {wait_time} seconds...")
                        time.sleep(wait_time + 2)
                    else:
                        time.sleep(3)
                except:
                    time.sleep(3)
                    
        except Exception as e:
            print(f"❌ Error in send_views: {e}")
        finally:
            self.is_sending = False

# Initialize
zefoy_api = ZefoyAPI()

@app.route('/')
def home():
    return jsonify({'status': 'running', 'service': 'Zefoy TikTok Views Bot'})

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'sending_active': zefoy_api.is_sending
    })

@app.route('/api/views', methods=['POST'])
def api_views():
    try:
        data = request.get_json()
        video_url = data.get('video_url') if data else None
        
        if not video_url:
            return jsonify({'success': False, 'error': 'video_url is required'}), 400
            
        if zefoy_api.is_sending:
            return jsonify({'success': False, 'error': 'Already sending views. Only one process allowed.'}), 409

        threading.Thread(target=zefoy_api.send_views, args=(video_url,), daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': 'Started sending views continuously',
            'video_url': video_url
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"🚀 Server running on port {port}")
    app.run(host='0.0.0.0', port=port)
