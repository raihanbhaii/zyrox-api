from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import os
import time
import re
import base64
from io import BytesIO
import requests
from requests import Session
import json

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

# HTML Template for web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok View Bot API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        
        .online {
            background: #4CAF50;
            color: white;
        }
        
        .offline {
            background: #f44336;
            color: white;
        }
        
        .unknown {
            background: #ff9800;
            color: white;
        }
        
        .endpoint {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 4px solid #4CAF50;
        }
        
        .method {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin-right: 15px;
            font-size: 14px;
        }
        
        .get {
            background: #61affe;
            color: white;
        }
        
        .post {
            background: #49cc90;
            color: white;
        }
        
        code {
            background: rgba(0, 0, 0, 0.3);
            padding: 3px 8px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
        }
        
        .input-group {
            margin: 20px 0;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.9);
            font-size: 16px;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
            margin-top: 10px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        #result {
            margin-top: 30px;
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            display: none;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
        }
        
        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .service-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .service-name {
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .loader {
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 3px solid white;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .stats {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }
        
        .stat-box {
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            flex: 1;
            margin: 0 10px;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .api-url {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 TikTok View Bot API</h1>
        
        <div class="service-grid" id="serviceStatus">
            <div class="service-card">
                <div class="service-name">Loading...</div>
                <div class="loader"></div>
            </div>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/api/status</code> - Check all services status
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span>
            <code>/api/views</code> - Send views to TikTok video
            <div class="api-url">
                Body: { "video_url": "https://...", "count": 100 }
            </div>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span>
            <code>/health</code> - Health check endpoint
        </div>
        
        <h3 style="margin-top: 30px;">📱 Try it now:</h3>
        
        <div class="input-group">
            <label for="videoUrl">TikTok Video URL:</label>
            <input type="text" id="videoUrl" placeholder="https://www.tiktok.com/@username/video/123456789" />
        </div>
        
        <div class="input-group">
            <label for="viewCount">Number of Views:</label>
            <input type="number" id="viewCount" value="10" min="1" max="1000" />
        </div>
        
        <div class="input-group">
            <label for="serviceSelect">Service:</label>
            <select id="serviceSelect">
                <option value="views">Views</option>
                <option value="followers">Followers</option>
                <option value="hearts">Hearts/Likes</option>
                <option value="shares">Shares</option>
            </select>
        </div>
        
        <button onclick="sendViews()" id="sendButton">
            🚀 Send Views
        </button>
        
        <div id="result"></div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number" id="totalSent">0</div>
                <div class="stat-label">Total Views Sent</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="successRate">0%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="uptime">-</div>
                <div class="stat-label">Uptime</div>
            </div>
        </div>
    </div>
    
    <script>
        let startTime = Date.now();
        let totalViewsSent = 0;
        let successfulRequests = 0;
        let totalRequests = 0;
        
        // Update uptime
        setInterval(() => {
            const uptime = Math.floor((Date.now() - startTime) / 1000);
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = uptime % 60;
            document.getElementById('uptime').textContent = 
                `${hours}h ${minutes}m ${seconds}s`;
        }, 1000);
        
        // Load service status
        async function loadStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.success) {
                    const serviceGrid = document.getElementById('serviceStatus');
                    serviceGrid.innerHTML = '';
                    
                    for (const [service, status] of Object.entries(data.services)) {
                        const card = document.createElement('div');
                        card.className = 'service-card';
                        card.innerHTML = `
                            <div class="service-name">${service.toUpperCase()}</div>
                            <span class="status-badge ${status}">${status}</span>
                        `;
                        serviceGrid.appendChild(card);
                    }
                }
            } catch (error) {
                console.error('Failed to load status:', error);
            }
        }
        
        async function sendViews() {
            const videoUrl = document.getElementById('videoUrl').value;
            const count = parseInt(document.getElementById('viewCount').value);
            const service = document.getElementById('serviceSelect').value;
            const button = document.getElementById('sendButton');
            const resultDiv = document.getElementById('result');
            
            if (!videoUrl) {
                alert('Please enter a TikTok video URL');
                return;
            }
            
            if (!videoUrl.includes('tiktok.com')) {
                alert('Please enter a valid TikTok URL');
                return;
            }
            
            button.disabled = true;
            button.innerHTML = '⏳ Processing...';
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loader"></div><p style="text-align:center;">Sending views...</p>';
            
            totalRequests++;
            
            try {
                const response = await fetch('/api/views', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        video_url: videoUrl,
                        count: count,
                        service: service
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    successfulRequests++;
                    totalViewsSent += data.views_sent || 0;
                    resultDiv.innerHTML = `
                        <h3 style="color: #4CAF50;">✅ Success!</h3>
                        <p>Views sent: ${data.views_sent || 0}</p>
                        <p>Message: ${data.message || 'Completed'}</p>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <h3 style="color: #f44336;">❌ Failed</h3>
                        <p>Error: ${data.error || 'Unknown error'}</p>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                }
                
                // Update stats
                document.getElementById('totalSent').textContent = totalViewsSent;
                const successRate = ((successfulRequests / totalRequests) * 100).toFixed(1);
                document.getElementById('successRate').textContent = successRate + '%';
                
            } catch (error) {
                resultDiv.innerHTML = `
                    <h3 style="color: #f44336;">❌ Error</h3>
                    <p>${error.message}</p>
                `;
            } finally {
                button.disabled = false;
                button.innerHTML = '🚀 Send Views';
            }
        }
        
        // Load status on page load
        loadStatus();
        // Refresh status every 30 seconds
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>
'''

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
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'cache-control': 'max-age=0',
        })
        
    def get_driver(self):
        """Create or return existing WebDriver instance"""
        if self.driver is None:
            self.driver = self._create_driver()
        return self.driver
    
    def _create_driver(self):
        """Create Chrome WebDriver with optimized settings for Docker"""
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
        
        # Memory optimization for Render free tier
        options.add_argument('--max_old_space_size=256')
        options.add_argument('--js-flags=--max-old-space-size=256')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-field-trial-config')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-breakpad')
        
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
            # Try with automatic driver management
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"Failed with webdriver-manager: {e}")
            # Fallback to default
            driver = webdriver.Chrome(options=options)
        
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # Execute anti-detection script
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def solve_captcha(self):
        """Solve Zefoy captcha using OCR service"""
        try:
            response = self.session.get(self.base_url)
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
            img_response = self.session.get(self.base_url + captcha_url)
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
            post_response = self.session.post(self.base_url, data=data)
            
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
    
    def get_service_status(self):
        """Get status of all services"""
        try:
            driver = self.get_driver()
            driver.get(self.base_url)
            
            # Wait for services to load
            wait = WebDriverWait(driver, 15)
            
            services = {
                "followers": "/html/body/div[6]/div/div[2]/div/div/div[2]/div/button",
                "hearts": "/html/body/div[6]/div/div[2]/div/div/div[3]/div/button",
                "comment_hearts": "/html/body/div[6]/div/div[2]/div/div/div[4]/div/button",
                "views": "/html/body/div[6]/div/div[2]/div/div/div[5]/div/button",
                "shares": "/html/body/div[6]/div/div[2]/div/div/div[6]/div/button",
                "favorites": "/html/body/div[6]/div/div[2]/div/div/div[7]/div/button",
            }
            
            statuses = {}
            for service_name, xpath in services.items():
                try:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    statuses[service_name] = "online" if element.is_enabled() else "offline"
                except:
                    statuses[service_name] = "offline"
            
            return {'success': True, 'services': statuses}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_views(self, video_url, count=100):
        """Send views to TikTok video"""
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
            
            # Send views
            sent_count = 0
            max_attempts = count * 2  # Prevent infinite loops
            attempts = 0
            
            while sent_count < count and attempts < max_attempts:
                try:
                    attempts += 1
                    
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
                            time.sleep(2)
                            
                        elif "seconds" in rate_text:
                            # Extract wait time
                            numbers = re.findall(r'(\d+)', rate_text)
                            if numbers:
                                wait_time = int(numbers[0])
                                time.sleep(wait_time + 2)
                        else:
                            time.sleep(3)
                            
                    except NoSuchElementException:
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"Error in send loop: {e}")
                    time.sleep(5)
            
            return {
                'success': True,
                'message': f'Successfully sent {sent_count} views',
                'views_sent': sent_count,
                'video_url': video_url
            }
            
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
    """Web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/google-chrome-stable')
    chrome_exists = os.path.exists(chrome_bin)
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'chrome_installed': chrome_exists,
        'chrome_path': chrome_bin,
        'environment': os.environ.get('RENDER', 'local')
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get service status"""
    try:
        status = zefoy_api.get_service_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/views', methods=['POST'])
def api_views():
    """Send views to TikTok video"""
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
        
        count = min(int(data.get('count', 100)), 1000)  # Limit for API protection
        service = data.get('service', 'views')
        
        if service == 'views':
            result = zefoy_api.send_views(video_url, count)
        else:
            # For other services, return not implemented
            result = {'success': False, 'error': f'Service {service} not implemented yet'}
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def api_test():
    """Test endpoint to verify API is working"""
    return jsonify({
        'success': True,
        'message': 'API is working',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '/': 'Web Interface',
            '/health': 'Health Check',
            '/api/status': 'Service Status',
            '/api/views': 'Send Views (POST)',
            '/api/test': 'Test Endpoint'
        }
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.teardown_appcontext
def cleanup(error=None):
    """Cleanup on app shutdown"""
    pass  # Don't cleanup on every request

# Cleanup handler for shutdown
import atexit
atexit.register(zefoy_api.cleanup)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
