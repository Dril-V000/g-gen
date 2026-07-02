import json
import time
import os
import random
import string
import logging
import uuid
import requests
from datetime import datetime
from faker import Faker
from playwright.sync_api import sync_playwright

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GmailCreator")

# متغيرات البيئة
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK:
    logger.error("❌ DISCORD_WEBHOOK_URL not set!")
    exit(1)

def generate_identity():
    """توليد هوية عشوائية"""
    fake = Faker()
    first = fake.first_name()
    last = fake.last_name()
    
    # كلمة مرور قوية
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(chars) for _ in range(14))
    
    return {
        "first_name": first,
        "last_name": last,
        "day": str(random.randint(1, 28)),
        "month": str(random.randint(1, 12)),
        "year": str(random.randint(1990, 2003)),
        "gender": random.choice(["Male", "Female"]),
        "password": password,
        "username": f"{first.lower()}{last.lower()}{random.randint(100, 999)}"
    }

def send_discord(data, screenshot=None):
    """إرسال النتيجة لديسكورد"""
    embed = {
        "title": "✅ Account Created!",
        "color": 3066993,
        "fields": [
            {"name": "📧 Email", "value": data.get('email', 'N/A'), "inline": False},
            {"name": "🔑 Password", "value": data.get('password', 'N/A'), "inline": False},
            {"name": "👤 Name", "value": f"{data.get('first_name', '')} {data.get('last_name', '')}", "inline": True},
            {"name": "📅 Birthday", "value": f"{data.get('day', '')}/{data.get('month', '')}/{data.get('year', '')}", "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    payload = {"embeds": [embed]}
    
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        if r.status_code == 204:
            logger.info("✅ Sent to Discord!")
        else:
            logger.error(f"❌ Discord error: {r.status_code}")
    except Exception as e:
        logger.error(f"❌ Send error: {e}")

def create_account():
    """إنشاء حساب جوجل"""
    
    identity = generate_identity()
    logger.info(f"🚀 Creating account for {identity['first_name']}...")
    
    with sync_playwright() as p:
        # تشغيل بدون واجهة (headless) لـ Render
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = context.new_page()
        
        try:
            # 1. الذهاب للتسجيل
            page.goto("https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp")
            time.sleep(3)
            
            # 2. تعبئة الاسم
            page.fill('input[name="firstName"]', identity['first_name'])
            page.fill('input[name="lastName"]', identity['last_name'])
            page.click('button:has-text("Next")')
            time.sleep(2)
            
            # 3. تاريخ الميلاد
            page.fill('input[name="day"]', identity['day'])
            page.fill('input[name="year"]', identity['year'])
            
            # اختيار الشهر
            page.click('#month')
            for _ in range(int(identity['month'])):
                page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            
            # اختيار الجنس
            page.click('#gender')
            if identity['gender'] == "Male":
                page.keyboard.press("ArrowDown")
            elif identity['gender'] == "Female":
                for _ in range(2):
                    page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            
            page.click('#birthdaygenderNext')
            time.sleep(2)
            
            # 4. اختيار اسم المستخدم
            page.fill('input[name="Username"]', identity['username'])
            time.sleep(1)
            page.click('#next')
            time.sleep(2)
            
            # 5. كلمة المرور
            page.fill('input[name="Passwd"]', identity['password'])
            page.fill('input[name="ConfirmPasswd"]', identity['password'])
            time.sleep(1)
            page.click('#createpasswordNext')
            time.sleep(3)
            
            try:
                page.click('button:has-text("I agree")')
                time.sleep(2)
            except:
                pass
            
            try:
                page.click('button:has-text("Skip")')
            except:
                pass
            
            account_data = {
                'email': f"{identity['username']}@gmail.com",
                'password': identity['password'],
                'first_name': identity['first_name'],
                'last_name': identity['last_name'],
                'day': identity['day'],
                'month': identity['month'],
                'year': identity['year']
            }
            
            screenshot = f"account_{int(time.time())}.png"
            page.screenshot(path=screenshot, full_page=True)
            
            send_discord(account_data, screenshot)
            
            if os.path.exists(screenshot):
                os.remove(screenshot)
            
            logger.info(f"✅ Account created: {account_data['email']}")
            browser.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            page.screenshot(path="error.png")
            browser.close()
            return False

def main():
    while True:
        try:
            success = create_account()
            if success:
                logger.info("💤 Waiting 3 hours before next...")
                time.sleep(10800)  # 3 ساعات
            else:
                logger.info("💤 Waiting 30 minutes after failure...")
                time.sleep(1800)  # 30 دقيقة
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}")
            time.sleep(600)  # 10 دقائق

if __name__ == "__main__":
    main()
