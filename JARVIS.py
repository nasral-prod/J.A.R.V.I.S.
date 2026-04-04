import speech_recognition as sr
import webbrowser
import os
import datetime
import pyautogui
import threading
import time
import urllib.parse
import re
import random
import sys
import subprocess
import json
import tempfile
import pygame
import psutil
from gtts import gTTS
import tkinter as tk
from tkinter import ttk, scrolledtext

try:
    import requests
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False
    print("⚠️ Для погоды установите: pip install requests")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except:
    HAS_PYPERCLIP = False
    print("⚠️ Для буфера обмена установите: pip install pyperclip")


class Config:
    WEATHER_API_KEY = "0ecf352d4edf6c2d202269221b9a713a"
    
    APP_PATHS = {
        "vscode": r"C:\Users\Илья\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "yandex_music": r"C:\Users\Илья\AppData\Local\Programs\YandexMusic\YandexMusic.exe",
        "telegram": r"C:\Users\Илья\AppData\Roaming\Telegram Desktop\Telegram.exe",
        "discord": r"C:\Users\Илья\AppData\Local\Discord\app-1.0.9166\Discord.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "calc": "calc.exe",
        "notepad": "notepad.exe",
        "cmd": "cmd.exe",
        "taskmgr": "taskmgr.exe",
    }
    
    MUSIC_FILE = r"backinblack.mp3"
    FULL_START_APPS = ["vscode", "chrome", "yandex_music"]
    
    SIMPLE_WAKE_WORDS = ["джарвис проснись", "привет джарвис", "эй джарвис"]
    FULL_WAKE_WORDS = ["просыпайся папочка вернулся", "просыпайся папочка"]
    
    EXIT_WORDS = ["выключись", "спи джарвис", "отключись", "до свидания джарвис", "хватит"]
    
    VOLUME_UP = ["громче", "увеличь громкость", "прибавь звук", "сделай громче"]
    VOLUME_DOWN = ["тише", "уменьши громкость", "убавь звук", "сделай тише"]
    VOLUME_MUTE = ["выключи звук", "без звука", "отключи звук", "мут"]
    VOLUME_UNMUTE = ["включи звук", "верни звук", "анмут"]


class VoiceEngine:
    def __init__(self):
        pygame.mixer.init()
        self.lang = 'ru'
    
    def say(self, text):
        print(f"🎙️ J.A.R.V.I.S.: {text}")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_path = fp.name
            tts = gTTS(text=text, lang=self.lang, slow=False)
            tts.save(temp_path)
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
            time.sleep(0.05)
            os.unlink(temp_path)
        except Exception as e:
            print(f"⚠️ Ошибка голоса: {e}")


class SpeechRecognizer:
    def __init__(self, status_callback=None):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = True
        self.status_callback = status_callback
        self._init_microphone()
    
    def _init_microphone(self):
        try:
            self.microphone = sr.Microphone()
            if self.status_callback:
                self.status_callback("🔧 Калибровка микрофона...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if self.status_callback:
                self.status_callback("✅ Микрофон готов")
        except Exception as e:
            print(f"⚠️ Микрофон не найден: {e}")
            self.microphone = None
            if self.status_callback:
                self.status_callback("⚠️ Микрофон не найден")
    
    def listen(self, timeout=3):
        if not self.is_listening or self.microphone is None:
            return ""
        try:
            with self.microphone as source:
                if self.status_callback:
                    self.status_callback("🎤 Слушаю...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            if self.status_callback:
                self.status_callback("🔄 Распознаю...")
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            if self.status_callback:
                self.status_callback(f"📝 {text}")
            return text.lower()
        except:
            return ""


class AppManager:
    @staticmethod
    def open_app(app_name):
        name_lower = app_name.lower()
        paths = Config.APP_PATHS
        
        if any(w in name_lower for w in ["vscode", "вижуал", "код"]):
            if os.path.exists(paths.get("vscode", "")):
                subprocess.Popen([paths["vscode"]])
                return "Visual Studio Code"
        
        elif any(w in name_lower for w in ["яндекс музыка", "яндекс музык"]):
            if os.path.exists(paths.get("yandex_music", "")):
                subprocess.Popen([paths["yandex_music"]])
                return "Яндекс Музыку"
            else:
                webbrowser.open("https://music.yandex.ru")
                return "Яндекс Музыку в браузере"
        
        elif any(w in name_lower for w in ["телеграм", "telegram", "тг"]):
            if os.path.exists(paths.get("telegram", "")):
                subprocess.Popen([paths["telegram"]])
                return "Telegram"
        
        elif any(w in name_lower for w in ["дискорд", "discord"]):
            if os.path.exists(paths.get("discord", "")):
                subprocess.Popen([paths["discord"]])
                return "Discord"
        
        elif any(w in name_lower for w in ["браузер", "хром", "chrome"]):
            webbrowser.open("https://www.google.com")
            return "браузер"
        
        elif any(w in name_lower for w in ["блокнот", "notepad"]):
            os.system("start notepad")
            return "блокнот"
        
        elif any(w in name_lower for w in ["калькулятор", "calc"]):
            os.system("start calc")
            return "калькулятор"
        
        elif any(w in name_lower for w in ["проводник", "explorer"]):
            os.system("start explorer")
            return "проводник"
        
        return None
    
    @staticmethod
    def open_folder(folder_name):
        name_lower = folder_name.lower()
        
        if "загрузк" in name_lower or "download" in name_lower:
            os.startfile(os.path.expanduser("~/Downloads"))
            return "загрузки"
        elif "рабочий стол" in name_lower or "desktop" in name_lower:
            os.startfile(os.path.expanduser("~/Desktop"))
            return "рабочий стол"
        elif "документ" in name_lower:
            os.startfile(os.path.expanduser("~/Documents"))
            return "документы"
        elif "музык" in name_lower:
            os.startfile(os.path.expanduser("~/Music"))
            return "музыку"
        
        return None


class VolumeController:
    @staticmethod
    def up(delta=10):
        for _ in range(delta // 2):
            pyautogui.press('volumeup')
    
    @staticmethod
    def down(delta=10):
        for _ in range(delta // 2):
            pyautogui.press('volumedown')
    
    @staticmethod
    def mute():
        pyautogui.press('volumemute')
    
    @staticmethod
    def unmute():
        pyautogui.press('volumemute')


class MediaControl:
    @staticmethod
    def play_pause():
        pyautogui.press('playpause')
    
    @staticmethod
    def next_track():
        pyautogui.press('nexttrack')
    
    @staticmethod
    def previous_track():
        pyautogui.press('prevtrack')


class ClipboardManager:
    @staticmethod
    def copy_text(text):
        if HAS_PYPERCLIP:
            pyperclip.copy(text)
            return True
        return False
    
    @staticmethod
    def paste():
        pyautogui.hotkey('ctrl', 'v')


class ReminderManager:
    def __init__(self):
        self.file = "reminders.json"
        self.reminders = self._load()
        self._start_checker()
    
    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)
    
    def add(self, text, time_str):
        self.reminders.append({"text": text, "time": time_str, "done": False})
        self._save()
        return True
    
    def _check(self):
        now = datetime.datetime.now().strftime("%H:%M")
        for r in self.reminders:
            if not r.get("done", False) and r["time"] == now:
                r["done"] = True
                self._save()
                return r["text"]
        return None
    
    def _start_checker(self, callback=None):
        def loop():
            while True:
                reminder = self._check()
                if reminder and callback:
                    callback(reminder)
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()


class WeatherManager:
    @staticmethod
    def get_weather(city="Балашов"):
        if not Config.WEATHER_API_KEY or not HAS_REQUESTS:
            return "API ключ погоды не настроен, сэр."
        
        city_map = {
            "балашов": "Balashov",
            "москва": "Moscow",
            "спб": "Saint Petersburg",
            "саратов": "Saratov",
            "волгоград": "Volgograd",
        }
        
        city_lower = city.lower().strip()
        city_eng = city_map.get(city_lower, city)
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city_eng}&appid={Config.WEATHER_API_KEY}&units=metric&lang=ru"
            r = requests.get(url, timeout=10)
            
            if r.status_code == 200:
                d = r.json()
                temp = int(d['main']['temp'])
                feels = int(d['main']['feels_like'])
                desc = d['weather'][0]['description']
                hum = d['main']['humidity']
                wind = d['wind']['speed']
                
                if "балашов" in city_lower:
                    return f"Погода в Балашове, сэр: {temp} градусов, {desc}. Ощущается как {feels}. Влажность {hum}%, ветер {wind} м/с."
                else:
                    return f"В {city} {temp}°, {desc}, влажность {hum}%, ветер {wind} м/с, сэр."
            else:
                return f"Город {city} не найден, сэр."
        except:
            return f"Не удалось получить погоду для {city}, сэр."


class NewsManager:
    @staticmethod
    def get_news():
        if not HAS_REQUESTS:
            return "Установите requests: pip install requests"
        
        try:
            import xml.etree.ElementTree as ET
            
            rss_urls = [
                "https://lenta.ru/rss",
                "https://ria.ru/export/rss2/index.xml",
                "https://www.interfax.ru/rss.asp",
            ]
            
            for url in rss_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        items = root.findall('.//item')[:5]
                        
                        if items:
                            news_list = []
                            for i, item in enumerate(items, 1):
                                title = item.find('title').text
                                if title:
                                    news_list.append(f"{i}. {title}")
                            
                            if news_list:
                                return "Новости: " + ". ".join(news_list)
                except:
                    continue
            
            return "Новости временно недоступны, сэр."
        except Exception as e:
            return f"Ошибка: {str(e)[:50]}"


class PasswordGenerator:
    @staticmethod
    def generate(length=12):
        import secrets
        import string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(length))


class SystemInfo:
    @staticmethod
    def get_battery():
        try:
            b = psutil.sensors_battery()
            return b.percent if b else 0
        except:
            return 0
    
    @staticmethod
    def get_cpu():
        return psutil.cpu_percent()
    
    @staticmethod
    def get_ram():
        return psutil.virtual_memory().percent


class CommandExecutor:
    def __init__(self, voice, log_callback=None, status_callback=None):
        self.voice = voice
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.is_active = False
        self.reminder_manager = ReminderManager()
        self.reminder_manager._start_checker(self.on_reminder)
        
        self.greetings = ["Приветствую, сэр!", "Слушаю вас, сэр!", "Система активирована, сэр!"]
        self.farewells = ["До свидания, сэр!", "Отключаюсь, сэр!"]
        self.jokes = [
            "Почему программисты не любят природу? Слишком много багов.",
            "Что сказал один бит другому? Мне тебя не хватает!",
            "Как отличить хорошего программиста от плохого? Плохой думает, что Java это остров."
        ]
    
    def log(self, text):
        if self.log_callback:
            self.log_callback(text)
    
    def on_reminder(self, text):
        self.voice.say(f"Напоминаю, сэр: {text}")
    
    def check(self, text, words):
        return any(w in text for w in words)
    
    def execute(self, command):
        if not command:
            return True
        
        if self.check(command, Config.SIMPLE_WAKE_WORDS):
            if not self.is_active:
                self.is_active = True
                self.voice.say(random.choice(self.greetings))
                self.voice.say("Я готов, сэр. Скажите команду.")
            return True
        
        if self.check(command, Config.FULL_WAKE_WORDS):
            if not self.is_active:
                self.is_active = True
                self.voice.say(random.choice(self.greetings))
                self._full_startup()
            return True
        
        if not self.is_active:
            return True
        
        if self.check(command, Config.EXIT_WORDS):
            self.voice.say(random.choice(self.farewells))
            self.is_active = False
            return False
        
        if self.check(command, Config.VOLUME_UP):
            numbers = re.findall(r'\d+', command)
            delta = int(numbers[0]) if numbers else 10
            VolumeController.up(delta)
            self.voice.say(f"Увеличиваю громкость на {delta}, сэр.")
        
        elif self.check(command, Config.VOLUME_DOWN):
            numbers = re.findall(r'\d+', command)
            delta = int(numbers[0]) if numbers else 10
            VolumeController.down(delta)
            self.voice.say(f"Уменьшаю громкость на {delta}, сэр.")
        
        elif self.check(command, Config.VOLUME_MUTE):
            VolumeController.mute()
            self.voice.say("Звук выключен, сэр.")
        
        elif self.check(command, Config.VOLUME_UNMUTE):
            VolumeController.unmute()
            self.voice.say("Звук включен, сэр.")
        
        elif self.check(command, ["пауза", "стоп"]):
            MediaControl.play_pause()
            self.voice.say("Пауза, сэр.")
        
        elif self.check(command, ["следующий трек", "следующая песня"]):
            MediaControl.next_track()
            self.voice.say("Следующий трек, сэр.")
        
        elif self.check(command, ["предыдущий трек", "прошлая песня"]):
            MediaControl.previous_track()
            self.voice.say("Предыдущий трек, сэр.")
        
        elif self.check(command, ["back in black", "бэк ин блэк"]):
            self.voice.say("Включаю Back in Black, сэр.")
            webbrowser.open("https://music.yandex.ru/search?text=AC/DC%20Back%20in%20Black")
        
        elif "включи музыку" in command:
            track = command.replace("включи музыку", "").strip()
            if track:
                self.voice.say(f"Ищу {track}, сэр.")
                webbrowser.open(f"https://music.yandex.ru/search?text={urllib.parse.quote(track)}")
            else:
                self.voice.say("Какую музыку включить, сэр?")
        
        elif self.check(command, ["открой", "запусти"]):
            name = command.replace("открой", "").replace("запусти", "").strip()
            result = AppManager.open_app(name)
            if result:
                self.voice.say(f"Открываю {result}, сэр.")
            elif "папк" in command:
                folder = command.replace("открой", "").replace("папку", "").strip()
                result = AppManager.open_folder(folder)
                if result:
                    self.voice.say(f"Открываю папку {result}, сэр.")
                else:
                    self.voice.say("Папка не найдена, сэр.")
            else:
                self.voice.say("Приложение не найдено, сэр.")
        
        elif self.check(command, ["ютуб", "youtube"]):
            webbrowser.open("https://www.youtube.com")
            self.voice.say("Открываю YouTube, сэр.")
        
        elif self.check(command, ["вк", "вконтакте"]):
            webbrowser.open("https://vk.com")
            self.voice.say("Открываю ВКонтакте, сэр.")
        
        elif self.check(command, ["найди", "загугли", "поищи"]):
            query = command
            for word in ["найди", "загугли", "поищи", "в интернете"]:
                query = query.replace(word, "")
            query = query.strip()
            if query:
                self.voice.say(f"Ищу {query} в интернете, сэр.")
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
            else:
                self.voice.say("Что найти, сэр?")
        
        elif "погода" in command:
            city_match = re.search(r'(?:в|в городе)\s+([а-яА-ЯёЁ\-]+)', command)
            if city_match:
                city = city_match.group(1)
            else:
                city = "Балашов"
                self.voice.say(f"Смотрю погоду в Балашове, сэр.")
            self.voice.say(WeatherManager.get_weather(city))
        
        elif self.check(command, ["новости", "что нового"]):
            self.voice.say("Загружаю последние новости, сэр.")
            self.voice.say(NewsManager.get_news())
        
        elif "напомни" in command:
            text = command.replace("напомни", "").strip()
            if text:
                remind_time = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%H:%M")
                self.reminder_manager.add(text, remind_time)
                self.voice.say(f"Напомню через 5 минут, сэр.")
            else:
                self.voice.say("Что напомнить, сэр?")
        
        elif self.check(command, ["скопируй", "скопировать"]):
            text = command.replace("скопируй", "").replace("скопировать", "").strip()
            if text and HAS_PYPERCLIP:
                ClipboardManager.copy_text(text)
                self.voice.say("Текст скопирован, сэр.")
            else:
                self.voice.say("Что скопировать, сэр?")
        
        elif "вставь" in command:
            ClipboardManager.paste()
            self.voice.say("Вставляю, сэр.")
        
        elif self.check(command, ["сгенерируй пароль", "пароль"]):
            nums = re.findall(r'\d+', command)
            length = int(nums[0]) if nums else 12
            pwd = PasswordGenerator.generate(length)
            self.voice.say(f"Пароль: {pwd}, сэр.")
            if HAS_PYPERCLIP:
                ClipboardManager.copy_text(pwd)
                self.voice.say("Пароль скопирован в буфер обмена, сэр.")
        
        elif self.check(command, ["который час", "сколько времени"]):
            now = datetime.datetime.now()
            self.voice.say(f"Сейчас {now.strftime('%H')} часов {now.strftime('%M')} минут, сэр.")
        
        elif self.check(command, ["какая сегодня дата", "какое число"]):
            now = datetime.datetime.now()
            months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                     'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            self.voice.say(f"Сегодня {now.day} {months[now.month-1]} {now.year} года, сэр.")
        
        elif self.check(command, ["заряд батареи", "батарея"]):
            self.voice.say(f"Заряд батареи {SystemInfo.get_battery()}%, сэр.")
        
        elif self.check(command, ["загрузка процессора", "процессор"]):
            self.voice.say(f"Загрузка процессора {SystemInfo.get_cpu()}%, сэр.")
        
        elif self.check(command, ["оперативная память", "оперативка"]):
            self.voice.say(f"Использовано {SystemInfo.get_ram()}% оперативной памяти, сэр.")
        
        elif self.check(command, ["заблокируй", "блокировка"]):
            self.voice.say("Блокирую компьютер, сэр.")
            pyautogui.hotkey('win', 'l')
        
        elif self.check(command, ["сделай скриншот", "скриншот"]):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pyautogui.screenshot().save(f"screenshot_{timestamp}.png")
            self.voice.say("Скриншот сохранён, сэр.")
        
        elif "выключи компьютер" in command:
            self.voice.say("Выключаю через 30 секунд. Скажите 'отмена', сэр.")
            threading.Timer(30, lambda: os.system("shutdown /s /t 1")).start()
        
        elif "отмена" in command:
            os.system("shutdown /a")
            self.voice.say("Отменено, сэр.")
        
        elif "как дела" in command:
            self.voice.say("Всё отлично, сэр!")
        elif "кто ты" in command:
            self.voice.say("Я J.A.R.V.I.S., ваш голосовой ассистент, сэр!")
        elif "спасибо" in command:
            self.voice.say("Всегда пожалуйста, сэр!")
        elif "шутку" in command:
            self.voice.say(random.choice(self.jokes))
        elif self.check(command, ["что умеешь", "команды", "помощь"]):
            self._help()
        elif len(command) > 3:
            self.voice.say("Команда не распознана, сэр. Скажите 'что ты умеешь'.")
        
        return True
    
    def _full_startup(self):
        self.voice.say("Запускаю все системы, сэр.")
        
        if os.path.exists(Config.MUSIC_FILE):
            self.voice.say("Включаю музыку, сэр.")
            os.startfile(Config.MUSIC_FILE)
        time.sleep(0.5)
        
        self.voice.say("Открываю браузер, сэр.")
        webbrowser.open("https://www.google.com")
        time.sleep(0.5)
        
        if "vscode" in Config.FULL_START_APPS and os.path.exists(Config.APP_PATHS.get("vscode", "")):
            self.voice.say("Запускаю Visual Studio Code, сэр.")
            subprocess.Popen([Config.APP_PATHS["vscode"]])
        time.sleep(0.5)
        
        if "yandex_music" in Config.FULL_START_APPS and os.path.exists(Config.APP_PATHS.get("yandex_music", "")):
            self.voice.say("Открываю Яндекс Музыку, сэр.")
            subprocess.Popen([Config.APP_PATHS["yandex_music"]])
        
        self.voice.say("Все системы запущены, сэр. Я слушаю вас.")
    
    def _help(self):
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                    J.A.R.V.I.S. - КОМАНДЫ                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🎤 ПРОСТАЯ АКТИВАЦИЯ: "Джарвис, проснись"                  ║
║  🚀 ПОЛНАЯ АКТИВАЦИЯ: "Просыпайся, папочка вернулся"        ║
║                                                              ║
║  🔊 ГРОМКОСТЬ: "Громче" / "Тише" / "Выключи звук"          ║
║  🎵 МУЗЫКА: "Включи Back in Black" / "Включи музыку..."    ║
║  🚀 ПРОГРАММЫ: "Открой блокнот" / "Открой VS Code"         ║
║  🌐 САЙТЫ: "Открой YouTube" / "Открой ВК"                  ║
║  🔍 ПОИСК: "Найди [запрос]" / "Загугли [запрос]"           ║
║  🌤️ ПОГОДА: "Погода" / "Погода в Балашове"                ║
║  📰 НОВОСТИ: "Новости" / "Что нового"                      ║
║  🗓️ НАПОМИНАНИЯ: "Напомни [текст]"                         ║
║  📋 БУФЕР: "Скопируй [текст]" / "Вставь"                   ║
║  🔐 ПАРОЛИ: "Сгенерируй пароль"                            ║
║  💻 СИСТЕМА: "Который час" / "Заряд батареи"               ║
║              "Заблокируй" / "Сделай скриншот"              ║
║              "Выключи компьютер" / "Отмена"                ║
║  💬 ОБЩЕНИЕ: "Как дела?" / "Кто ты?" / "Расскажи шутку"    ║
║  🔴 ВЫХОД: "Выключись" / "Спи, Джарвис"                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(help_text)
        self.voice.say("Вот список моих команд, сэр. Я отправил его на экран.")


class JarvisGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. MAX")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.configure(bg='#0a0a1a')
        
        self.is_listening = False
        self.listening_thread = None
        
        self._setup_ui()
        self._init_assistant()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _setup_ui(self):
        header = tk.Frame(self.root, bg='#1a1a2e', height=100)
        header.pack(fill='x', padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="⚡ J.A.R.V.I.S. MAX ⚡", 
                font=('Arial', 28, 'bold'), fg='#00ff00', bg='#1a1a2e').pack(pady=10)
        tk.Label(header, text="Голосовой ассистент в стиле Тони Старка", 
                font=('Arial', 10), fg='#888888', bg='#1a1a2e').pack()
        
        status_frame = tk.Frame(self.root, bg='#16213e', relief=tk.RAISED, bd=2)
        status_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(status_frame, text="СТАТУС", font=('Arial', 10, 'bold'), 
                fg='#ffaa00', bg='#16213e').pack(side='left', padx=15, pady=10)
        
        self.status_var = tk.StringVar(value="🔴 Не активен")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                     font=('Arial', 12), fg='#ff4444', bg='#16213e')
        self.status_label.pack(side='left', padx=10, pady=10)
        
        self.mic_indicator = tk.Label(status_frame, text="🎤", font=('Arial', 18), 
                                      fg='#888888', bg='#16213e')
        self.mic_indicator.pack(side='right', padx=15, pady=5)
        
        wake_frame = tk.Frame(self.root, bg='#0f3460', relief=tk.RAISED, bd=2)
        wake_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(wake_frame, text="🔑 КЛЮЧЕВЫЕ ФРАЗЫ", 
                font=('Arial', 10, 'bold'), fg='#ffaa00', bg='#0f3460').pack(pady=5)
        tk.Label(wake_frame, text="🎤 Простая активация: \"Джарвис, проснись\"", 
                font=('Arial', 11), fg='#00ff00', bg='#0f3460').pack(pady=2)
        tk.Label(wake_frame, text="🚀 Полная активация: \"Просыпайся, папочка вернулся\"", 
                font=('Arial', 11), fg='#00ff00', bg='#0f3460').pack(pady=2)
        
        log_frame = tk.LabelFrame(self.root, text="📝 ЛОГ КОМАНД", 
                                  font=('Arial', 10, 'bold'), fg='#00ff00', bg='#1a1a2e')
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, 
                                                   bg='#0a0a1a', fg='#00ff00', 
                                                   font=('Consolas', 9))
        self.log_area.pack(fill='both', expand=True, padx=5, pady=5)
        
        btn_frame = tk.Frame(self.root, bg='#1a1a2e')
        btn_frame.pack(pady=20)
        
        self.start_btn = tk.Button(btn_frame, text="🎤 ЗАПУСТИТЬ", 
                                   command=self.start_listening,
                                   bg='#0f3460', fg='#00ff00', 
                                   font=('Arial', 11, 'bold'), padx=20, pady=10)
        self.start_btn.pack(side='left', padx=10)
        
        stop_btn = tk.Button(btn_frame, text="⏹️ ОСТАНОВИТЬ", 
                             command=self.stop_listening,
                             bg='#e94560', fg='white', 
                             font=('Arial', 11, 'bold'), padx=20, pady=10)
        stop_btn.pack(side='left', padx=10)
        
        help_btn = tk.Button(btn_frame, text="❓ КОМАНДЫ", 
                             command=self.show_commands,
                             bg='#0f3460', fg='#00ff00', 
                             font=('Arial', 11, 'bold'), padx=20, pady=10)
        help_btn.pack(side='left', padx=10)
    
    def _init_assistant(self):
        self.voice = VoiceEngine()
        self.listener = SpeechRecognizer(status_callback=self.update_status)
        self.executor = CommandExecutor(self.voice, log_callback=self.add_log, status_callback=self.update_status)
        self.add_log("🚀 J.A.R.V.I.S. MAX готов к работе")
    
    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
    
    def update_status(self, status):
        self.status_var.set(status)
        if "Слушаю" in status:
            self.mic_indicator.config(fg='#00ff00')
        elif "Готов" in status:
            self.mic_indicator.config(fg='#00ff00')
        else:
            self.mic_indicator.config(fg='#888888')
        self.add_log(f"Статус: {status}")
    
    def start_listening(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.listener.is_listening = True
        self.start_btn.config(text="🎤 СЛУШАЮ...", state=tk.DISABLED)
        self.add_log("🚀 Запуск голосового ассистента...")
        self.listening_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listening_thread.start()
    
    def stop_listening(self):
        self.is_listening = False
        self.listener.is_listening = False
        self.start_btn.config(text="🎤 ЗАПУСТИТЬ", state=tk.NORMAL)
        self.add_log("⏹️ Ассистент остановлен")
        self.update_status("🔴 Остановлен")
    
    def _listen_loop(self):
        while self.is_listening:
            command = self.listener.listen(timeout=2)
            if command:
                result = self.executor.execute(command)
                if result is False:
                    self.stop_listening()
                    break
            time.sleep(0.1)
    
    def show_commands(self):
        cmd_window = tk.Toplevel(self.root)
        cmd_window.title("J.A.R.V.I.S. - Команды")
        cmd_window.geometry("650x550")
        cmd_window.configure(bg='#0a0a1a')
        
        tk.Label(cmd_window, text="📋 СПИСОК КОМАНД", 
                font=('Arial', 16, 'bold'), fg='#00ff00', bg='#0a0a1a').pack(pady=10)
        
        text_area = scrolledtext.ScrolledText(cmd_window, bg='#0a0a1a', fg='#00ff00', 
                                              font=('Consolas', 10))
        text_area.pack(fill='both', expand=True, padx=10, pady=10)
        
        commands = """
╔══════════════════════════════════════════════════════════════╗
║                    J.A.R.V.I.S. - КОМАНДЫ                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🎤 ПРОСТАЯ АКТИВАЦИЯ: "Джарвис, проснись"                  ║
║  🚀 ПОЛНАЯ АКТИВАЦИЯ: "Просыпайся, папочка вернулся"        ║
║                                                              ║
║  🔊 ГРОМКОСТЬ: "Громче" / "Тише" / "Выключи звук"          ║
║  🎵 МУЗЫКА: "Включи Back in Black" / "Включи музыку..."    ║
║  🚀 ПРОГРАММЫ: "Открой блокнот" / "Открой VS Code"         ║
║  🌐 САЙТЫ: "Открой YouTube" / "Открой ВК"                  ║
║  🔍 ПОИСК: "Найди [запрос]" / "Загугли [запрос]"           ║
║  🌤️ ПОГОДА: "Погода" / "Погода в Балашове"                ║
║  📰 НОВОСТИ: "Новости" / "Что нового"                      ║
║  🗓️ НАПОМИНАНИЯ: "Напомни [текст]"                         ║
║  📋 БУФЕР: "Скопируй [текст]" / "Вставь"                   ║
║  🔐 ПАРОЛИ: "Сгенерируй пароль"                            ║
║  💻 СИСТЕМА: "Который час" / "Заряд батареи"               ║
║              "Заблокируй" / "Сделай скриншот"              ║
║              "Выключи компьютер" / "Отмена"                ║
║  💬 ОБЩЕНИЕ: "Как дела?" / "Кто ты?" / "Расскажи шутку"    ║
║  🔴 ВЫХОД: "Выключись" / "Спи, Джарвис"                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        text_area.insert(tk.END, commands)
        text_area.config(state=tk.DISABLED)
        
        close_btn = tk.Button(cmd_window, text="ЗАКРЫТЬ", command=cmd_window.destroy,
                             bg='#0f3460', fg='white', font=('Arial', 10, 'bold'), padx=20, pady=5)
        close_btn.pack(pady=10)
    
    def on_closing(self):
        self.is_listening = False
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if 'TCL_LIBRARY' not in os.environ:
        tcl_path = r"C:\Users\Илья\AppData\Local\Programs\Python\Python312\tcl\tcl8.6"
        tk_path = r"C:\Users\Илья\AppData\Local\Programs\Python\Python312\tcl\tk8.6"
        if os.path.exists(tcl_path):
            os.environ['TCL_LIBRARY'] = tcl_path
        if os.path.exists(tk_path):
            os.environ['TK_LIBRARY'] = tk_path
    
    try:
        app = JarvisGUI()
        app.run()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажмите Enter для выхода...")