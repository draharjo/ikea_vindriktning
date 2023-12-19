import time
from machine import UART, Pin
import utime
import network
import urequests as requests
import ntptime
from dht import DHT11, InvalidChecksum

# Define the onboard LED pin
led = machine.Pin("LED", machine.Pin.OUT)
admin_id = "YOUR TELEGRAM ID"

def indicate_error():
    led.value(1); time.sleep(3); led.value(0); time.sleep(1); led.value(1); time.sleep(3); led.value(0)
def getting_sensor():
    led.value(1); time.sleep(0.5); led.value(0); time.sleep(0.5); led.value(1); time.sleep(0.5); led.value(0)
    
# Function to load registered users from a .txt file
def load_registered_users():
    try:
        with open('registered_users.txt', 'r') as file:
            registered_users = eval(file.read())
            return registered_users if registered_users else {}
    except OSError:
        return {}
    
def get_temp_humidity():
    sensor = DHT11(Pin(28, Pin.OUT, Pin.PULL_DOWN))
    try:
        temp = sensor.temperature
        humidity = sensor.humidity
        print("Temperature: {}°C   Humidity: {:.0f}% ".format(temp, humidity))
        return temp, humidity
    except:
        return None, None
    
# Function to save registered users to a .txt file
def save_registered_users(users):
    with open('registered_users.txt', 'w') as file:
        file.write(str(users))
        
# Function to handle incoming messages
def handle_message(message):
    user = message['from']
    user_id = user['id']
    text = message.get('text', '').lower()  # Get message text (convert to lowercase for case-insensitive comparison)

    if text == 'unsubscribe':
        # Remove user from the registered_users list if they send 'unsubscribe'
        if user_id in registered_users:
            del registered_users[user_id]
            send_message(user_id, 'You have been unsubscribed.')
            notify_admin(f"Registered users: {registered_users}")
            save_registered_users(registered_users)
        else:
            send_message(user_id, 'You are not currently subscribed.')
        
    elif text == 'subscribe':
        # Register user if they send 'subscribe'
        if user_id not in registered_users:
            username = user.get('username', '')
            first_name = user['first_name']
            registered_users[user_id] = {'username': username, 'first_name': first_name}
            send_message(user_id, f"Hi {first_name}, we'll send u PM2.5 info at CBD Calathea every 5 min!")
            
            # Check if last_message exists and send it upon subscription
            if last_message:
                send_data(user_id, last_message)
            notify_admin(f"Registered users: {registered_users}")
            save_registered_users(registered_users)
        else:
            send_message(user_id, 'You are already subscribed.')
    else:
        send_message(user_id, 'Invalid command. Please use "subscribe" or "unsubscribe".')
        
def send_message(chat_id, text):
    try:
        payload = {'chat_id': chat_id,'text': text}
        response = requests.post(telegram_api_url + 'sendMessage', json=payload)
        response.close()
    except:
        pass
    
def notify_admin(text, chat_id = admin_id):
    try:
        payload = {'chat_id': chat_id,'text': text}
        response = requests.post(telegram_api_url + 'sendMessage', json=payload)
        response.close()
    except:
        pass
        
# Function to fetch updates
def fetch_updates(offset=None):
    try:
        if offset is not None:
            response = requests.get(telegram_api_url + f'getUpdates?offset={offset}')
            updatenya = response.json()
            response.close()
        else:
            response = requests.get(telegram_api_url + 'getUpdates')
            updatenya = response.json()
            response.close()
        return updatenya
    except:
        pass
    
def send_data(chatId, message):
    try:
        sendURL = 'https://api.telegram.org/bot' + bot_token + '/sendMessage'
        response = requests.post(sendURL+"?chat_id=" + str(chatId) + "&text=" + message)
        response.close()
    except:
        print("error")
def get_time():
    JAKARTA_OFFSET = 7 * 3600  # Jakarta's timezone offset in seconds (UTC+7)
    now = utime.localtime()  # Get current time in UTC

    # Add timezone offset (Adjust hours, minutes, and seconds)
    adjusted_time = (now[0], now[1], now[2], now[3] + (JAKARTA_OFFSET // 3600),now[4] + (JAKARTA_OFFSET % 3600) // 60, now[5])

    # Ensure correct hour format (0-23) for the adjusted time
    adjusted_hour = adjusted_time[3] % 24
    formatted_datetime = "{:02d} {} {} {:02d}:{:02d}".format(adjusted_time[2], month_name[adjusted_time[1]], adjusted_time[0],adjusted_hour, adjusted_time[4])
    return formatted_datetime


def connect_to_wifi(timeout=30):
    start_time = time.time()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        if time.time() - start_time >= timeout:
            return None
        time.sleep(1)
    return wlan

def get_pm25_value():
    getting_sensor()
    def valid_header(d):
        return (d[0] == 0x16 and d[1] == 0x11 and d[2] == 0x0B)
    
    uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
    v = False
    while v is not True:
        data = uart0.read(32)
        if data is not None:
            v = valid_header(data)
    
    measurements = [0, 0, 0, 0, 0]  # Circular buffer to store PM2.5 values
    measurement_idx = 0
    start_read = True
    
    while True:
        if start_read is True:
            pm25 = (data[5] << 8) | data[6]
            measurements[measurement_idx] = pm25
            if measurement_idx == 4:
                start_read = False
            measurement_idx = (measurement_idx + 1) % 5
        else:
            break
    return pm25

def categorize_pm25(pm25_value):
    if pm25_value >= 0 and pm25_value <= 35:
        return "Good"
    elif pm25_value <= 85:
        return "Ok"
    elif pm25_value > 85:
        return "Not good"
    
#PARAMETER
month_name = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
SSID = 'YOUR WIFI NAME'
PASSWORD = 'YOUR WIFI PASSWORD'
bot_token = 'YOUR BOT TOKEN'
chat_id = ['YOUR CHAT ID']
telegram_api_url = f"https://api.telegram.org/bot{bot_token}/"
registered_users = load_registered_users()

# Initialize Wi-Fi
connection_timeout = 60  # Set a reasonable connection timeout in seconds
wlan = None
while wlan is None:
    wlan = connect_to_wifi(timeout=connection_timeout)
    if wlan is None:
        print('Wi-Fi connection timed out. Retrying...')
        wlan = network.WLAN(network.STA_IF)
        wlan.active(False)
        time.sleep(5)
        wlan.active(True)
        wlan.connect(SSID, PASSWORD)
        print(wlan)
print('Connected to Wi-Fi:', wlan.ifconfig())

# Fetch time from NTP server
ntptime.settime()
last_update_id = None
last_sensor_data_time = 0
sensor_data_interval = 300  # 5 minutes in seconds
last_message = None

while True:
    try:
        current_time = time.time()
        # Read messages at any interval
        updates = fetch_updates(offset=last_update_id)
        if updates.get('result') is not None:
            for update in updates['result']:
                handle_message(update['message'])
                last_update_id = update['update_id'] + 1

        # Send sensor data every 5 minutes
        if current_time - last_sensor_data_time >= sensor_data_interval:
            try:
                pm25 = get_pm25_value()
                temp, humidity = get_temp_humidity()
                pm25_category = categorize_pm25(pm25)
                if pm25 != 0:
                    latest_pm25 = pm25
                time_now = get_time()
                message = f"[{time_now}] PM2.5 ~ {latest_pm25} μg/m³, {pm25_category}, {temp}°C, {humidity}%"
                last_message = message
                for chat_id in registered_users:
                    send_data(chat_id, message)
                print(message)
                last_sensor_data_time = current_time  # Update the last sent sensor data time

            except OSError as e:
                pass  # Handle OSError as per your requirements

        # Sleep to avoid high CPU usage
        time.sleep(1)  # Adjust sleep duration as needed
    except:
        pass

