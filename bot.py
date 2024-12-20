import telebot
import requests
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import qrcode
from io import BytesIO
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Bot token
TOKEN = os.getenv('TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')

# Initialize bot
bot = telebot.TeleBot(TOKEN)

def create_keyboard():
    """Create keyboard with ticket button."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("دریافت بلیت غذا"))
    return keyboard

def generate_qr_image(data):
    """Generate QR code image from data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

@bot.message_handler(commands=['start'])
def start(message):
    """Handle /start command."""
    try:
        logger.info(f"Start command received from user {message.from_user.id}")
        bot.reply_to(
            message,
            "به ربات بلیت غذا خوش آمدید!",
            reply_markup=create_keyboard()
        )
        logger.info("Welcome message sent successfully")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

@bot.message_handler(func=lambda message: message.text == "دریافت بلیت غذا")
def request_id(message):
    """Handle ticket button press."""
    try:
        logger.info(f"Button pressed by user {message.from_user.id}")
        bot.reply_to(message, "لطفا کد ملی خود را وارد کنید")
        # Register the next step handler
        bot.register_next_step_handler(message, process_id)
        logger.info("ID request message sent successfully")
    except Exception as e:
        logger.error(f"Error in request_id: {e}")

def process_id(message):
    """Process the national ID and fetch tickets."""
    try:
        id_number = message.text
        logger.info(f"Processing ID from user {message.from_user.id}: {id_number}")
        
        # Make API request
        response = requests.post(
            f"{API_BASE_URL}/user-tickets/",
            json={"id_number": id_number}
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Received data for user: {data['username']}")
            
            # Send user info
            user_info = f"اطلاعات کاربر:\nنام: {data['first_name']} {data['last_name']}"
            bot.reply_to(message, user_info)
            
            # Send tickets information
            for ticket in data['tickets']:
                status_text = "معتبر" if ticket['status'] == 'valid' else "استفاده شده"
                ticket_info = (
                    f"🎫 بلیت {ticket['ticket_type']['title']}\n"
                    f"وضعیت: {status_text}\n"
                )
                
                # Generate and send QR code as photo
                try:
                    qr_data = ticket['qr_code_url']
                    qr_image = generate_qr_image(qr_data)
                    bot.send_photo(
                        message.chat.id,
                        qr_image,
                        caption=ticket_info,
                        reply_to_message_id=message.message_id
                    )
                    logger.info(f"QR code sent for ticket {ticket['ticket_type']['title']}")
                except Exception as e:
                    logger.error(f"Error sending QR code: {e}")
                    bot.reply_to(message, "خطا در ارسال QR code")
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            bot.reply_to(message, "خطا در دریافت اطلاعات. لطفا دوباره تلاش کنید.")
            
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        bot.reply_to(message, "خطایی رخ داد. لطفا دوباره تلاش کنید.")

@bot.message_handler(func=lambda message: True)
def echo(message):
    """Handle all other messages."""
    logger.info(f"Received message: {message.text}")
    bot.reply_to(message, "لطفا از دکمه دریافت بلیت غذا استفاده کنید")

if __name__ == "__main__":
    logger.info("Bot starting...")
    try:
        # Verify bot token
        bot_info = bot.get_me()
        logger.info(f"Bot verified: @{bot_info.username}")
        
        # Start polling
        logger.info("Starting polling...")
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
