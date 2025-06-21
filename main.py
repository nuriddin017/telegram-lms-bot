import os
import json
import logging
from dotenv import load_dotenv
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from telebot import types

# Environment variables yuklash
load_dotenv()

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable topilmadi!")

bot = telebot.TeleBot(BOT_TOKEN)

# Google Sheets sozlamalari
SCOPE = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

SPREADSHEET_NAME = os.getenv('GOOGLE_SPREADSHEET_NAME', "O'quvchilar Ma'lumotlari")

# Foydalanuvchi holatini saqlash
user_states = {}

def get_google_credentials():
    """Google Sheets uchun credentials olish"""
    try:
        # Railway muhitida environment variables orqali
        if os.getenv('RAILWAY_ENVIRONMENT'):
            creds_dict = {
                "type": "service_account",
                "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL')}"
            }
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        else:
            # Local development uchun JSON fayl
            return ServiceAccountCredentials.from_json_keyfile_name('credentials/service-account.json', SCOPE)
    except Exception as e:
        logger.error(f"Google credentials xatosi: {e}")
        return None

def get_google_sheet():
    """Google Sheets bilan bog'lanish"""
    try:
        creds = get_google_credentials()
        if not creds:
            return None
            
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        logger.error(f"Google Sheets bog'lanish xatosi: {e}")
        return None

def clean_phone_number(phone):
    """Telefon raqamini tozalash va formatlash"""
    if not phone:
        return ""
    
    # Faqat raqamlarni qoldirish
    phone = re.sub(r'[^\d]', '', str(phone))
    
    # Turli formatlarni standart formatga o'tkazish
    if phone.startswith('998') and len(phone) == 12:
        phone = '+' + phone
    elif phone.startswith('8') and len(phone) == 12:
        phone = '+99' + phone[1:]
    elif len(phone) == 9:
        phone = '+998' + phone
    elif len(phone) == 12 and not phone.startswith('998'):
        phone = '+' + phone
    
    return phone

def find_student_by_phone(phone_number):
    """Telefon raqam bo'yicha o'quvchini topish"""
    sheet = get_google_sheet()
    if not sheet:
        logger.error("Google Sheets bog'lanish xatosi")
        return None
    
    try:
        all_records = sheet.get_all_records()
        clean_phone = clean_phone_number(phone_number)
        
        logger.info(f"Qidirilayotgan telefon: {clean_phone}")
        
        for record in all_records:
            record_phone = clean_phone_number(record.get('Telefon', ''))
            
            if record_phone == clean_phone:
                logger.info(f"O'quvchi topildi: {record.get('Ism', '')} {record.get('Familiya', '')}")
                return record
        
        logger.info("O'quvchi topilmadi")
        return None
    except Exception as e:
        logger.error(f"Ma'lumot qidirish xatosi: {e}")
        return None

def format_student_info(student_data):
    """O'quvchi ma'lumotlarini chiroyli formatlash"""
    if not student_data:
        return "❌ Ma'lumot topilmadi"
    
    info = f"""
🎓 **Xush kelibsiz, {student_data.get('Ism', 'N/A')} {student_data.get('Familiya', 'N/A')}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Shaxsiy Ma'lumotlar:**
• Ism-familiya: {student_data.get('Ism', 'N/A')} {student_data.get('Familiya', 'N/A')}
• ID raqam: {student_data.get('ID', 'N/A')}
• Telefon: {student_data.get('Telefon', 'N/A')}
• Email: {student_data.get('Email', 'N/A')}

📚 **Ta'lim Ma'lumotlari:**
• Guruh: {student_data.get('Guruh', 'N/A')}
• Kurs: {student_data.get('Kurs', 'N/A')}
• Baholar: {student_data.get('Baholar', 'N/A')}
• Davomat: {student_data.get('Davomat', 'N/A')}%

💰 **Moliyaviy Ma'lumotlar:**
• To'lov holati: {student_data.get('Tolov_holati', 'N/A')}
• To'lov miqdori: {student_data.get('Tolov_miqdori', 'N/A')} so'm
• Keyingi to'lov: {student_data.get('Keyingi_tolov', 'N/A')}

📅 **Muhim Sanalar:**
• Ro'yxatdan o'tgan: {student_data.get('Royxat_sana', 'N/A')}
• Oxirgi dars: {student_data.get('Oxirgi_dars', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Statistika:**
• Umumiy darslar: {student_data.get('Umumiy_darslar', 'N/A')}
• Qatnashgan darslar: {student_data.get('Qatnashgan_darslar', 'N/A')}
• O'rtacha baho: {student_data.get('Ortacha_baho', 'N/A')}
"""
    return info

def create_main_menu():
    """Asosiy menyu tugmalarini yaratish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📊 Mening ma\'lumotlarim', '📞 Telefon o\'zgartirish')
    markup.add('📚 Baholarim', '💰 To\'lov holati')
    markup.add('📅 Dars jadvali', '📋 Yangiliklar')
    markup.add('❓ Yordam', '🚪 Chiqish')
    return markup

def create_phone_request_markup():
    """Telefon raqam so'rash tugmasini yaratish"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    markup.add(button)
    markup.add("✍️ Qo'lda yozish")
    return markup

# Bot handlerlari
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Botni ishga tushirish"""
    user_id = message.from_user.id
    user_states[user_id] = 'waiting_phone'
    
    logger.info(f"Yangi foydalanuvchi: {message.from_user.username} ({user_id})")
    
    welcome_text = f"""
🎓 **O'quvchilar Ma'lumotlari Botiga Xush Kelibsiz!**

Salom, {message.from_user.first_name}! 

Bu bot orqali siz o'zingiz haqingizdagi barcha ma'lumotlarni oson ko'rishingiz mumkin:
• 📊 Baholar va o'rtacha ball
• 💰 To'lov holati  
• 📅 Dars jadvali
• 📞 Bog'lanish ma'lumotlari

🔐 **Xavfsizlik uchun telefon raqamingizni tasdiqlang:**

Telefon raqamingizni yuboring yoki pastdagi tugmani bosing 👇
"""
    
    bot.send_message(message.chat.id, welcome_text, 
                    reply_markup=create_phone_request_markup(), 
                    parse_mode='Markdown')

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    """Telefon kontakt yuborilganda"""
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    
    # Telefon raqamni formatlash
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    logger.info(f"Kontakt olindi: {phone_number}")
    
    # O'quvchini qidirish
    student_data = find_student_by_phone(phone_number)
    
    if student_data:
        user_states[user_id] = 'authenticated'
        user_states[f"{user_id}_data"] = student_data
        
        success_message = f"✅ Muvaffaqiyatli tasdiqlandi!\nXush kelibsiz, {student_data.get('Ism', '')} {student_data.get('Familiya', '')}!"
        
        bot.send_message(message.chat.id, success_message, reply_markup=create_main_menu())
        
        # Ma'lumotlarni yuborish
        info = format_student_info(student_data)
        bot.send_message(message.chat.id, info, parse_mode='Markdown')
    else:
        error_message = f"""❌ Kechirasiz, {phone_number} raqami bizning tizimda ro'yxatdan o'tmagan.

📞 Iltimos, quyidagilarni tekshiring:
• To'g'ri telefon raqam kiritdingizmi?
• Ro'yxatdan o'tganingizga ishonchingiz komilmi?

❓ Yordam kerak bo'lsa, admin bilan bog'laning: @{os.getenv('ADMIN_USERNAME', 'admin')}

🔄 Qaytadan urinish uchun /start ni bosing."""
        
        bot.send_message(message.chat.id, error_message, reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: message.text == "✍️ Qo'lda yozish")
def manual_phone_input(message):
    """Qo'lda telefon raqam kiritish"""
    user_id = message.from_user.id
    user_states[user_id] = 'entering_phone'
    
    manual_input_text = """📱 Telefon raqamingizni kiriting:

📝 **Formatlar:**
• +998901234567
• 998901234567  
• 901234567

❌ Bekor qilish uchun /start ni bosing"""
    
    bot.send_message(message.chat.id, manual_input_text,
                    reply_markup=types.ReplyKeyboardRemove(),
                    parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'entering_phone')
def process_manual_phone(message):
    """Qo'lda kiritilgan telefon raqamni qayta ishlash"""
    user_id = message.from_user.id
    phone_number = message.text.strip()
    
    # Telefon raqam formatini tekshirish
    if not re.match(r'^[\+]?[0-9\s\-\(\)]{9,15}$', phone_number):
        bot.send_message(message.chat.id, 
                        "❌ Noto'g'ri format!\n\n"
                        "📝 To'g'ri format: +998901234567\n"
                        "Qaytadan kiriting:")
        return
    
    # O'quvchini qidirish
    student_data = find_student_by_phone(phone_number)
    
    if student_data:
        user_states[user_id] = 'authenticated'
        user_states[f"{user_id}_data"] = student_data
        
        bot.send_message(message.chat.id, "✅ Muvaffaqiyatli tasdiqlandi!", 
                        reply_markup=create_main_menu())
        
        # Ma'lumotlarni yuborish
        info = format_student_info(student_data)
        bot.send_message(message.chat.id, info, parse_mode='Markdown')
    else:
        clean_phone = clean_phone_number(phone_number)
        error_msg = f"""❌ {clean_phone} raqami tizimda topilmadi.

🔄 Boshqa raqam bilan urinib ko'ring yoki admin bilan bog'laning.

📞 Admin: @{os.getenv('ADMIN_USERNAME', 'admin')}
🏠 Bosh sahifaga qaytish: /start"""
        
        bot.send_message(message.chat.id, error_msg)

# Autentifikatsiya qilingan foydalanuvchilar uchun menyu handlerlari
@bot.message_handler(func=lambda message: message.text == "📊 Mening ma'lumotlarim" and user_states.get(message.from_user.id) == 'authenticated')
def show_my_info(message):
    """O'quvchining to'liq ma'lumotlarini ko'rsatish"""
    user_id = message.from_user.id
    student_data = user_states.get(f"{user_id}_data")
    
    if student_data:
        info = format_student_info(student_data)
        bot.send_message(message.chat.id, info, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Ma'lumot topilmadi. Qaytadan /start ni bosing.")

@bot.message_handler(func=lambda message: message.text == "📚 Baholarim" and user_states.get(message.from_user.id) == 'authenticated')
def show_grades(message):
    """Faqat baholarni ko'rsatish"""
    user_id = message.from_user.id
    student_data = user_states.get(f"{user_id}_data")
    
    if student_data:
        grades_info = f"""
📚 **{student_data.get('Ism', '')} {student_data.get('Familiya', '')} - Baholar**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Barcha baholar:** {student_data.get('Baholar', 'Ma\'lumot yo\'q')}
⭐ **O'rtacha baho:** {student_data.get('Ortacha_baho', 'Hisoblash mumkin emas')}
📈 **Eng yuqori baho:** {student_data.get('Eng_yuqori_baho', 'N/A')}
📉 **Eng past baho:** {student_data.get('Eng_past_baho', 'N/A')}

🎯 **Baholash mezonlari:**
• 5 - A'lo (90-100%)
• 4 - Yaxshi (70-89%)
• 3 - Qoniqarli (60-69%)
• 2 - Qoniqarsiz (0-59%)
"""
        bot.send_message(message.chat.id, grades_info, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "💰 To'lov holati" and user_states.get(message.from_user.id) == 'authenticated')
def show_payment_status(message):
    """To'lov holatini ko'rsatish"""
    user_id = message.from_user.id
    student_data = user_states.get(f"{user_id}_data")
    
    if student_data:
        payment_info = f"""
💰 **To'lov Ma'lumotlari**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 **Joriy holat:** {student_data.get('Tolov_holati', 'N/A')}
💵 **To'lov miqdori:** {student_data.get('Tolov_miqdori', 'N/A')} so'm
📅 **Keyingi to'lov:** {student_data.get('Keyingi_tolov', 'N/A')}
📊 **To'langan:** {student_data.get('Tolangan_summa', 'N/A')} so'm
📋 **Qarz:** {student_data.get('Qarz', 'N/A')} so'm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 To'lov bo'yicha savollar uchun:
🏢 Ofis: +998 XX XXX XX XX
💬 Admin: @{os.getenv('ADMIN_USERNAME', 'admin')}
"""
        bot.send_message(message.chat.id, payment_info, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🚪 Chiqish")
def logout(message):
    """Tizimdan chiqish"""
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    user_states.pop(f"{user_id}_data", None)
    
    bot.send_message(message.chat.id, 
                    "👋 Tizimdan muvaffaqiyatli chiqdingiz!\n\n"
                    "🔄 Qaytadan kirish uchun /start ni bosing.",
                    reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) != 'authenticated')
def handle_unauthorized(message):
    """Autentifikatsiya qilinmagan xabarlar"""
    bot.send_message(message.chat.id, 
                    "🔐 Avval telefon raqamingizni tasdiqlang!\n\n"
                    "Boshlash uchun /start ni bosing.",
                    reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Boshqa barcha xabarlar"""
    user_id = message.from_user.id
    
    if user_states.get(user_id) == 'authenticated':
        bot.send_message(message.chat.id, 
                        "🤔 Tushunmadim. Pastdagi tugmalardan birini tanlang:",
                        reply_markup=create_main_menu())
    else:
        bot.send_message(message.chat.id, 
                        "🔐 Avval telefon raqamingizni tasdiqlang!\n"
                        "Boshlash uchun /start ni bosing.")

# Xatoliklarni boshqarish
@bot.middleware_handler(update_types=['message'])
def error_handler(bot_instance, message):
    try:
        pass
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        try:
            bot.send_message(message.chat.id, 
                           "❌ Bot xatolikka duch keldi. Keyinroq urinib ko'ring.")
        except:
            pass

# Botni ishga tushirish
if __name__ == '__main__':
    logger.info("🤖 Bot ishga tushmoqda...")
    logger.info("📱 Telefon autentifikatsiyasi yoqilgan")
    
    # Railway muhiti tekshiruvi
    if os.getenv('RAILWAY_ENVIRONMENT'):
        logger.info("🌐 Railway serverda ishlayapti")
    else:
        logger.info("💻 Local development muhitida")
    
    try:
        # Botni ishga tushirish
        bot.remove_webhook()
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"❌ Bot xatoligi: {e}")
