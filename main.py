#!/usr/bin/env python3
import os
import sys
import re
import json
import random
import time
import threading
import datetime
import subprocess
import tempfile
import urllib.parse
import webbrowser
import socket
import getpass
import platform
import secrets
import string
import xml.etree.ElementTree as ET
import fnmatch

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
os.environ["QT_OPENGL"] = "software"

try:
    import PySide6
    pyside_path = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(pyside_path, "plugins")
    if os.path.exists(plugin_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
except ImportError:
    pass

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot, Signal

import speech_recognition as sr
import pyautogui
import psutil
import requests
import pygame
try:
    import pyperclip
    HAS_PYPERCLIP = True
except:
    HAS_PYPERCLIP = False
from gtts import gTTS


class Config:
    WEATHER_API_KEY = "0ecf352d4edf6c2d202269221b9a713a"
    MUSIC_FILE = r"backinblack.mp3"
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
        "paint": "mspaint.exe",
        "wordpad": "write.exe",
    }
    SIMPLE_WAKE_WORDS = ["джарвис проснись", "привет джарвис", "эй джарвис", "джарвис активируйся"]
    FULL_WAKE_WORDS = ["просыпайся папочка вернулся", "просыпайся папочка", "джарвис я вернулся"]
    EXIT_WORDS = ["выключись", "спи джарвис", "отключись", "джарвис выключись"]
    VOLUME_UP = ["громче", "увеличь громкость", "прибавь звук"]
    VOLUME_DOWN = ["тише", "уменьши громкость", "убавь звук"]
    VOLUME_MUTE = ["выключи звук", "мут", "без звука"]
    VOLUME_UNMUTE = ["включи звук", "верни звук", "анмут"]


class VoiceEngine:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.available = True
            print("Голосовой движок инициализирован")
        except Exception as e:
            self.available = False
            print(f"Ошибка инициализации звука: {e}")
    def say(self, text):
        print(f"J.A.R.V.I.S.: {text}")
        if not self.available:
            return
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                tts = gTTS(text=text, lang='ru', slow=False)
                tts.save(fp.name)
                fp.close()
                pygame.mixer.music.load(fp.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                os.unlink(fp.name)
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")


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
                self.status_callback("Калибровка микрофона...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if self.status_callback:
                self.status_callback("Микрофон готов")
        except Exception as e:
            print(f"Ошибка микрофона: {e}")
            self.microphone = None
            if self.status_callback:
                self.status_callback("Микрофон не найден")
    def listen(self, timeout=3):
        if not self.is_listening or self.microphone is None:
            return ""
        try:
            with self.microphone as source:
                if self.status_callback:
                    self.status_callback("Слушаю...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            if self.status_callback:
                self.status_callback("Распознаю...")
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            if self.status_callback:
                self.status_callback(f"Вы: {text}")
            return text.lower()
        except Exception:
            return ""


class AppManager:
    _cache = {}

    @staticmethod
    def _find_in_path(executable):
        """Поиск в PATH через where (Windows)"""
        try:
            result = subprocess.run(['where', executable], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        return None

    @staticmethod
    def _find_in_common_locations(executable, subpaths=None):
        """Поиск в Program Files, Program Files (x86), LocalAppData"""
        base_dirs = [
            os.environ.get('ProgramFiles', 'C:\\Program Files'),
            os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'),
            os.environ.get('LocalAppData', os.path.expanduser('~\\AppData\\Local')),
            os.environ.get('AppData', os.path.expanduser('~\\AppData\\Roaming'))
        ]
        if subpaths is None:
            subpaths = [executable, f"*\\{executable}"]
        for base in base_dirs:
            for sub in subpaths:
                path = os.path.join(base, sub)
                if '*' in path:
                    # простой glob (только для одного уровня)
                    base_dir = os.path.dirname(path)
                    pattern = os.path.basename(path)
                    if os.path.exists(base_dir):
                        for item in os.listdir(base_dir):
                            if fnmatch.fnmatch(item, pattern):
                                full = os.path.join(base_dir, item)
                                if os.path.isfile(full):
                                    return full
                else:
                    if os.path.isfile(path):
                        return path
        return None

    @staticmethod
    def _find_vscode():
        # Поиск Code.exe
        path = AppManager._find_in_path('code.cmd') or AppManager._find_in_path('code')
        if path:
            return path
        # Поиск в Program Files
        return AppManager._find_in_common_locations('Code.exe', [
            'Microsoft VS Code\\Code.exe',
            'Microsoft VS Code Insiders\\Code - Insiders.exe'
        ])

    @staticmethod
    def _find_yandex_music():
        return AppManager._find_in_common_locations('YandexMusic.exe', [
            'Programs\\YandexMusic\\YandexMusic.exe',
            'YandexMusic\\YandexMusic.exe'
        ])

    @staticmethod
    def _find_telegram():
        path = AppManager._find_in_path('Telegram.exe')
        if path:
            return path
        return AppManager._find_in_common_locations('Telegram.exe', [
            'Telegram Desktop\\Telegram.exe'
        ])

    @staticmethod
    def _find_discord():
        path = AppManager._find_in_path('Discord.exe')
        if path:
            return path
        return AppManager._find_in_common_locations('Discord.exe', [
            'Discord\\app-*\\Discord.exe',
            'Discord\\Discord.exe'
        ])

    @staticmethod
    def _find_chrome():
        path = AppManager._find_in_path('chrome.exe')
        if path:
            return path
        return AppManager._find_in_common_locations('chrome.exe', [
            'Google\\Chrome\\Application\\chrome.exe'
        ])

    @staticmethod
    def open_app(name):
        name_lower = name.lower()

        # Visual Studio Code
        if any(w in name_lower for w in ["vscode", "вижуал студио", "код", "vs code"]):
            path = AppManager._find_vscode()
            if path:
                subprocess.Popen([path])
                return "Visual Studio Code"
            else:
                return None

        # Яндекс Музыка
        elif any(w in name_lower for w in ["яндекс музыка", "яндекс музык"]):
            path = AppManager._find_yandex_music()
            if path:
                subprocess.Popen([path])
                return "Яндекс Музыку"
            else:
                webbrowser.open("https://music.yandex.ru")
                return "Яндекс Музыку в браузере"

        # Telegram
        elif any(w in name_lower for w in ["телеграм", "telegram", "тг"]):
            path = AppManager._find_telegram()
            if path:
                subprocess.Popen([path])
                return "Telegram"
            else:
                return None

        # Discord
        elif any(w in name_lower for w in ["дискорд", "discord"]):
            path = AppManager._find_discord()
            if path:
                subprocess.Popen([path])
                return "Discord"
            else:
                return None

        # Браузер (Chrome или по умолчанию)
        elif any(w in name_lower for w in ["браузер", "хром", "chrome"]):
            path = AppManager._find_chrome()
            if path:
                subprocess.Popen([path])
                return "Google Chrome"
            else:
                webbrowser.open("https://www.google.com")
                return "браузер по умолчанию"

        # Системные приложения (не требуют поиска)
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

class VolumeController:
    @staticmethod
    def up(): pyautogui.press('volumeup'); pyautogui.press('volumeup')
    @staticmethod
    def down(): pyautogui.press('volumedown'); pyautogui.press('volumedown')
    @staticmethod
    def mute(): pyautogui.press('volumemute')
    @staticmethod
    def unmute(): pyautogui.press('volumemute')


class MediaControl:
    @staticmethod
    def play_pause(): pyautogui.press('playpause')
    @staticmethod
    def next_track(): pyautogui.press('nexttrack')
    @staticmethod
    def previous_track(): pyautogui.press('prevtrack')


class ClipboardManager:
    @staticmethod
    def copy(text):
        if HAS_PYPERCLIP: pyperclip.copy(text); return True
        return False
    @staticmethod
    def paste(): pyautogui.hotkey('ctrl','v')


class ReminderManager:
    def __init__(self, callback):
        self.file = "reminders.json"
        self.callback = callback
        self.reminders = self._load()
        self._start()
    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file,'r',encoding='utf-8') as f: return json.load(f)
            except: pass
        return []
    def _save(self):
        with open(self.file,'w',encoding='utf-8') as f: json.dump(self.reminders,f,ensure_ascii=False,indent=2)
    def add(self, text, time_str):
        self.reminders.append({"text":text,"time":time_str,"done":False})
        self._save()
    def _check(self):
        now = datetime.datetime.now().strftime("%H:%M")
        for r in self.reminders:
            if not r.get("done",False) and r["time"] == now:
                r["done"]=True
                self._save()
                if self.callback: self.callback(r["text"])
    def _start(self):
        def loop():
            while True:
                self._check()
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()


class WeatherManager:
    @staticmethod
    def get(city="Балашов"):
        if not Config.WEATHER_API_KEY: return "API ключ не настроен"
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={Config.WEATHER_API_KEY}&units=metric&lang=ru"
            r = requests.get(url, timeout=10)
            if r.status_code==200:
                d=r.json()
                return f"{city}: {int(d['main']['temp'])}°, {d['weather'][0]['description']}, влажность {d['main']['humidity']}%"
            return f"Город {city} не найден"
        except: return "Ошибка погоды"


class NewsManager:
    @staticmethod
    def get():
        try:
            r = requests.get("https://lenta.ru/rss", timeout=10)
            root = ET.fromstring(r.content)
            items = root.findall('.//item')[:3]
            news = [item.find('title').text for item in items if item.find('title') is not None]
            return "Новости: " + ". ".join(news) if news else "Новости не загружены"
        except: return "Новости временно недоступны"


class PasswordGenerator:
    @staticmethod
    def generate(length=12):
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(length))


class SystemInfo:
    @staticmethod
    def get_cpu(): return psutil.cpu_percent()
    @staticmethod
    def get_ram(): return psutil.virtual_memory().percent
    @staticmethod
    def get_battery():
        b = psutil.sensors_battery()
        return b.percent if b else 0
    @staticmethod
    def get_disk(): return psutil.disk_usage('/').percent
    @staticmethod
    def get_ip():
        try: return socket.gethostbyname(socket.gethostname())
        except: return "неизвестно"
    @staticmethod
    def get_user(): return getpass.getuser()


class PollinationsAI:
    @staticmethod
    def ask(question):
        try:
            url = "https://text.pollinations.ai/"
            payload = {"messages":[{"role":"system","content":"Ты J.A.R.V.I.S. Отвечай кратко, по-русски, обращайся 'сэр'."},{"role":"user","content":question}]}
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code==200:
                try: return r.json()["choices"][0]["message"]["content"]
                except: return r.text
            return "Ошибка API"
        except: return "Не удалось связаться с нейросетью"


class CommandExecutor:
    def __init__(self, voice, log_callback, status_callback, ai_mode_callback):
        self.voice = voice
        self.log = log_callback
        self.status_callback = status_callback
        self.ai_mode_callback = ai_mode_callback
        self.is_active = False
        self.ai_mode = False
        self.reminder = ReminderManager(self.on_reminder)
        self.greetings = ["Приветствую, сэр!","Слушаю вас, сэр!","Система активирована, сэр!"]
        self.farewells = ["До свидания, сэр!","Отключаюсь, сэр!","Всего хорошего, сэр!"]
        self.jokes = [
            "Почему программисты не любят природу? Слишком много багов.",
            "Что сказал один бит другому? Мне тебя не хватает!",
            "Как отличить хорошего программиста от плохого? Плохой думает, что Java это остров.",
            "Почему программист перешёл дорогу? Чтобы оптимизировать маршрут.",
            "Как программисты поздравляют с днём рождения? Желаю, чтобы все баги были фичами!"
        ]
        self.quotes = [
            "Единственный способ делать великую работу — любить то, что вы делаете. Стив Джобс",
            "Гениальность состоит в умении отличать трудное от невозможного. Наполеон Бонапарт",
            "Я не потерпел неудачу. Я просто нашёл 10 000 способов, которые не работают. Томас Эдисон"
        ]
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
            self.ai_mode = False
            self.ai_mode_callback(False)
            return False
        if any(w in command for w in ["включи ии","включи нейросеть","активируй ии"]):
            self.ai_mode = True
            self.ai_mode_callback(True)
            self.voice.say("Режим ИИ активирован. Задавайте любые вопросы.")
            return True
        if any(w in command for w in ["выключи ии","выключи нейросеть","деактивируй ии"]):
            self.ai_mode = False
            self.ai_mode_callback(False)
            self.voice.say("Режим ИИ деактивирован.")
            return True
        if self.ai_mode:
            self.voice.say("Спрашиваю...")
            answer = PollinationsAI.ask(command)
            self.voice.say(answer)
            return True
        if self.check(command, Config.VOLUME_UP):
            VolumeController.up()
            self.voice.say("Громче, сэр.")
        elif self.check(command, Config.VOLUME_DOWN):
            VolumeController.down()
            self.voice.say("Тише, сэр.")
        elif self.check(command, Config.VOLUME_MUTE):
            VolumeController.mute()
            self.voice.say("Звук выключен.")
        elif self.check(command, Config.VOLUME_UNMUTE):
            VolumeController.unmute()
            self.voice.say("Звук включен.")
        elif self.check(command, ["пауза","стоп"]):
            MediaControl.play_pause()
            self.voice.say("Пауза.")
        elif self.check(command, ["следующий трек","следующая песня"]):
            MediaControl.next_track()
            self.voice.say("Следующий трек.")
        elif self.check(command, ["предыдущий трек","прошлая песня"]):
            MediaControl.previous_track()
            self.voice.say("Предыдущий трек.")
        elif "back in black" in command:
            webbrowser.open("https://music.yandex.ru/search?text=AC/DC%20Back%20in%20Black")
            self.voice.say("Включаю Back in Black.")
        elif "включи музыку" in command:
            track = command.replace("включи музыку","").strip()
            if track:
                webbrowser.open(f"https://music.yandex.ru/search?text={urllib.parse.quote(track)}")
                self.voice.say(f"Ищу {track}.")
            else:
                self.voice.say("Какую музыку?")
        elif self.check(command, ["открой","запусти"]):
            name = command.replace("открой","").replace("запусти","").strip()
            res = AppManager.open_app(name)
            if res:
                self.voice.say(f"Открываю {res}.")
            elif "папк" in command:
                folder = command.replace("открой","").replace("папку","").strip()
                res = AppManager.open_folder(folder)
                if res:
                    self.voice.say(f"Открываю папку {res}.")
                else:
                    self.voice.say("Папка не найдена.")
            else:
                self.voice.say("Приложение не найдено.")
        elif self.check(command, ["ютуб","youtube"]):
            webbrowser.open("https://www.youtube.com")
            self.voice.say("Открываю YouTube.")
        elif self.check(command, ["вк","вконтакте"]):
            webbrowser.open("https://vk.com")
            self.voice.say("Открываю ВК.")
        elif self.check(command, ["найди","загугли"]):
            q = command
            for w in ["найди","загугли","поищи"]: q = q.replace(w,"")
            q = q.strip()
            if q:
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
                self.voice.say(f"Ищу {q}.")
            else:
                self.voice.say("Что найти?")
        elif "погода" in command:
            city = re.search(r'в\s+([а-яА-ЯёЁ\-]+)', command)
            city = city.group(1) if city else "Балашов"
            self.voice.say(WeatherManager.get(city))
        elif self.check(command, ["новости","что нового"]):
            self.voice.say(NewsManager.get())
        elif "напомни" in command:
            text = command.replace("напомни","").strip()
            if text:
                remind_time = (datetime.datetime.now() + datetime.timedelta(minutes=5)).strftime("%H:%M")
                self.reminder.add(text, remind_time)
                self.voice.say("Напомню через 5 минут.")
            else:
                self.voice.say("Что напомнить?")
        elif self.check(command, ["скопируй","скопировать"]):
            text = command.replace("скопируй","").replace("скопировать","").strip()
            if text and HAS_PYPERCLIP:
                ClipboardManager.copy(text)
                self.voice.say("Текст скопирован.")
            else:
                self.voice.say("Что скопировать?")
        elif "вставь" in command:
            ClipboardManager.paste()
            self.voice.say("Вставляю.")
        elif self.check(command, ["сгенерируй пароль","пароль"]):
            pwd = PasswordGenerator.generate(12)
            self.voice.say(f"Пароль: {pwd}")
            if HAS_PYPERCLIP:
                ClipboardManager.copy(pwd)
                self.voice.say("Пароль скопирован.")
        elif self.check(command, ["который час","сколько времени"]):
            now = datetime.datetime.now().strftime("%H:%M")
            self.voice.say(f"Сейчас {now}, сэр.")
        elif self.check(command, ["какая сегодня дата","какое число"]):
            now = datetime.datetime.now().strftime("%d.%m.%Y")
            self.voice.say(f"Сегодня {now}.")
        elif self.check(command, ["заряд батареи","батарея"]):
            self.voice.say(f"Заряд {SystemInfo.get_battery()}%.")
        elif self.check(command, ["загрузка процессора","процессор"]):
            self.voice.say(f"CPU {SystemInfo.get_cpu()}%.")
        elif self.check(command, ["оперативная память","оперативка"]):
            self.voice.say(f"RAM {SystemInfo.get_ram()}%.")
        elif "заблокируй" in command:
            pyautogui.hotkey('win','l')
            self.voice.say("Блокирую.")
        elif "скриншот" in command:
            name = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot().save(name)
            self.voice.say("Скриншот сохранён.")
        elif "выключи компьютер" in command:
            self.voice.say("Выключаю через 30 секунд. Скажите 'отмена'.")
            threading.Timer(30, lambda: os.system("shutdown /s /t 1")).start()
        elif "отмена" in command:
            os.system("shutdown /a")
            self.voice.say("Отменено.")
        elif "сверни окна" in command:
            pyautogui.hotkey('win','d')
            self.voice.say("Свернул все окна, сэр.")
        elif "разверни окна" in command:
            pyautogui.hotkey('win','d')
            self.voice.say("Показал рабочий стол, сэр.")
        elif "переключи окно" in command:
            pyautogui.hotkey('alt','tab')
            self.voice.say("Переключаю окна, сэр.")
        elif "закрой окно" in command:
            pyautogui.hotkey('alt','f4')
            self.voice.say("Закрыл активное окно, сэр.")
        elif "открой папку загрузки" in command:
            os.startfile(os.path.expanduser("~/Downloads"))
            self.voice.say("Открываю папку Загрузки, сэр.")
        elif "открой папку документы" in command:
            os.startfile(os.path.expanduser("~/Documents"))
            self.voice.say("Открываю Документы, сэр.")
        elif "открой папку видео" in command:
            os.startfile(os.path.expanduser("~/Videos"))
            self.voice.say("Открываю Видео, сэр.")
        elif "открой папку музыка" in command:
            os.startfile(os.path.expanduser("~/Music"))
            self.voice.say("Открываю Музыку, сэр.")
        elif "открой папку изображения" in command:
            os.startfile(os.path.expanduser("~/Pictures"))
            self.voice.say("Открываю Изображения, сэр.")
        elif "открой paint" in command:
            os.system("start mspaint")
            self.voice.say("Открываю Paint, сэр.")
        elif "открой wordpad" in command:
            os.system("start write")
            self.voice.say("Открываю WordPad, сэр.")
        elif "очисти корзину" in command:
            os.system("cmd /c rd /s /q C:\\$Recycle.bin 2>nul")
            self.voice.say("Корзина очищена, сэр.")
        elif "перезагрузи проводник" in command:
            os.system("taskkill /f /im explorer.exe & start explorer.exe")
            self.voice.say("Проводник перезагружен, сэр.")
        elif "запусти диспетчер задач" in command:
            os.system("start taskmgr")
            self.voice.say("Открываю диспетчер задач, сэр.")
        elif "запусти командную строку" in command:
            os.system("start cmd")
            self.voice.say("Открываю командную строку, сэр.")
        elif "запусти powershell" in command:
            os.system("start powershell")
            self.voice.say("Открываю PowerShell, сэр.")
        elif "посчитай" in command or "сколько будет" in command:
            expr = re.sub(r'(посчитай|сколько будет|вычисли)', '', command).strip()
            expr = expr.replace('х', '*').replace('Х', '*').replace('×', '*')
            expr = expr.replace('плюс', '+').replace('минус', '-')
            expr = expr.replace('умножить на', '*').replace('разделить на', '/')
            try:
                result = eval(expr)
                self.voice.say(f"Результат: {result}, сэр.")
            except:
                self.voice.say("Не удалось вычислить, сэр.")
        elif "таймер на" in command or "засеки" in command:
            nums = re.findall(r'\d+', command)
            if nums:
                seconds = int(nums[0])
                self.voice.say(f"Запускаю таймер на {seconds} секунд, сэр.")
                def timer_callback():
                    self.voice.say(f"Таймер на {seconds} секунд закончился, сэр.")
                threading.Timer(seconds, timer_callback).start()
            else:
                self.voice.say("На сколько секунд установить таймер, сэр?")
        elif "цитата" in command or "мудрая мысль" in command:
            self.voice.say(random.choice(self.quotes))
        elif "анекдот" in command:
            self.voice.say(random.choice(self.jokes))
        elif "курс доллара" in command or "курс евро" in command:
            try:
                url = "https://www.cbr-xml-daily.ru/daily_json.js"
                r = requests.get(url, timeout=10)
                data = r.json()
                usd = data["Valute"]["USD"]["Value"]
                eur = data["Valute"]["EUR"]["Value"]
                self.voice.say(f"Доллар: {usd:.2f} рублей, Евро: {eur:.2f} рублей, сэр.")
            except:
                self.voice.say("Не удалось получить курс валют, сэр.")
        elif "спящий режим" in command:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            self.voice.say("Перевожу компьютер в спящий режим, сэр.")
        elif "гибернация" in command:
            os.system("shutdown /h")
            self.voice.say("Перехожу в гибернацию, сэр.")
        elif "выйти из системы" in command:
            os.system("shutdown /l")
            self.voice.say("Выхожу из системы, сэр.")
        elif "мой ip" in command:
            ip = SystemInfo.get_ip()
            self.voice.say(f"Ваш IP адрес: {ip}, сэр.")
        elif "имя компьютера" in command:
            self.voice.say(f"Имя компьютера: {socket.gethostname()}, сэр.")
        elif "скриншот через" in command:
            nums = re.findall(r'\d+', command)
            if nums:
                delay = int(nums[0])
                self.voice.say(f"Сделаю скриншот через {delay} секунд, сэр.")
                threading.Timer(delay, lambda: pyautogui.screenshot().save(f"screenshot_delay_{int(time.time())}.png")).start()
            else:
                self.voice.say("Через сколько секунд сделать скриншот, сэр?")
        elif "как дела" in command:
            self.voice.say("Всё отлично, сэр!")
        elif "кто ты" in command:
            self.voice.say("Я J.A.R.V.I.S., ваш ассистент.")
        elif "спасибо" in command:
            self.voice.say("Всегда пожалуйста.")
        elif "шутку" in command:
            self.voice.say(random.choice(self.jokes))
        elif self.check(command, ["что умеешь","команды","помощь"]):
            self.voice.say("Я умею: управлять громкостью, включать музыку, открывать программы, искать в интернете, показывать погоду и новости, напоминать, генерировать пароли, делать скриншоты, блокировать ПК и многое другое. Скажите 'включи ии' для вопросов.")
        else:
            self.voice.say("Команда не распознана. Скажите 'что умеешь'.")
        return True
    def _full_startup(self):
        self.voice.say("Запускаю системы.")
        if os.path.exists(Config.MUSIC_FILE):
            os.startfile(Config.MUSIC_FILE)
        webbrowser.open("https://www.google.com")
        if os.path.exists(Config.APP_PATHS.get("vscode","")):
            subprocess.Popen([Config.APP_PATHS["vscode"]])
        if os.path.exists(Config.APP_PATHS.get("yandex_music","")):
            subprocess.Popen([Config.APP_PATHS["yandex_music"]])
        self.voice.say("Все системы запущены.")


class JarvisAPI(QObject):
    logMessage = Signal(str)
    statusChanged = Signal(str, bool)
    aiModeChanged = Signal(bool)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ai_mode = False
        self._listener_thread = None
        self._is_listening = False
        self.voice = VoiceEngine()
        self.executor = None
        self.listener = None
        self._init_components()
    def _init_components(self):
        self.executor = CommandExecutor(
            voice=self.voice,
            log_callback=self._on_log,
            status_callback=self._on_status,
            ai_mode_callback=self._on_ai_mode_change
        )
        self.listener = SpeechRecognizer(status_callback=self._on_status)
    def _on_log(self, msg):
        self.logMessage.emit(msg)
    def _on_status(self, status):
        self.statusChanged.emit(status, self._ai_mode)
    def _on_ai_mode_change(self, mode):
        self._ai_mode = mode
        self.aiModeChanged.emit(mode)
    @Slot(str, result=str)
    def execute_command(self, command):
        result = self.executor.execute(command)
        return str(result)
    @Slot(result=dict)
    def get_system_info(self):
        return {
            "cpu": SystemInfo.get_cpu(),
            "ram": SystemInfo.get_ram(),
            "battery": SystemInfo.get_battery(),
            "disk": SystemInfo.get_disk(),
            "ip": SystemInfo.get_ip(),
            "user": SystemInfo.get_user()
        }
    @Slot()
    def start_listening(self):
        if self._is_listening:
            return
        self._is_listening = True
        self.listener.is_listening = True
        def listen_loop():
            while self._is_listening:
                cmd = self.listener.listen(timeout=2)
                if cmd:
                    self.executor.execute(cmd)
                time.sleep(0.1)
        self._listener_thread = threading.Thread(target=listen_loop, daemon=True)
        self._listener_thread.start()
        self._on_log("Прослушивание микрофона запущено.")
    @Slot()
    def stop_listening(self):
        self._is_listening = False
        self.listener.is_listening = False
        if self._listener_thread:
            self._listener_thread.join(timeout=1)
        self._on_log("Прослушивание микрофона остановлено.")


HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>J.A.R.V.I.S.</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Exo+2:wght@300;400;600;800&family=Russo+One&family=Roboto:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            user-select: none;
        }
        body {
            font-family: 'Exo 2', 'Roboto', sans-serif;
            background: #0a0c12;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
            position: relative;
        }
        .bg-gradient {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 20% 30%, #0a1620, #05070a);
            z-index: 0;
        }
        .grid-lines {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }
        .app {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            padding: 20px;
        }
        .title-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(0,255,170,0.4);
        }
        .title-bar h1 {
            font-family: 'Orbitron', 'Russo One', monospace;
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, #00ffcc, #00aa88);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            letter-spacing: 2px;
        }
        .title-bar span {
            font-family: 'Exo 2', monospace;
            color: #6c8a9e;
            font-size: 14px;
            background: rgba(0,0,0,0.5);
            padding: 6px 14px;
            border-radius: 30px;
            border: 1px solid rgba(0,255,170,0.3);
        }
        .grid {
            display: flex;
            flex: 1;
            gap: 24px;
            min-height: 0;
        }
        .left-panel {
            width: 340px;
            background: rgba(8,12,20,0.85);
            border-radius: 28px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            border: 1px solid rgba(0,255,170,0.3);
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        }
        .status-card {
            background: rgba(0,20,30,0.5);
            border-radius: 24px;
            padding: 20px;
            text-align: center;
        }
        .mic-icon {
            font-size: 80px;
            margin: 10px 0;
            filter: drop-shadow(0 0 5px #00ffaa);
            transition: 0.2s;
        }
        .mic-icon.listening {
            text-shadow: 0 0 20px #00ffaa;
            animation: pulse 1.2s infinite;
        }
        @keyframes pulse {
            0%,100% { transform: scale(1); opacity:0.8; }
            50% { transform: scale(1.05); opacity:1; }
        }
        .status-text {
            font-size: 24px;
            font-weight: bold;
            font-family: 'Exo 2', monospace;
        }
        .status-active { color: #00ffaa; text-shadow: 0 0 3px #00ffaa; }
        .status-inactive { color: #ff5566; }
        .sys-card {
            background: rgba(0,20,30,0.5);
            border-radius: 24px;
            padding: 16px;
        }
        .sys-title {
            font-family: 'Orbitron', monospace;
            color: #00ffaa;
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: 1px;
        }
        .sys-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,255,170,0.2);
        }
        .sys-label { color: #8aa; font-size:14px; }
        .sys-value { color: #0fa; font-family: monospace; font-weight: bold; }

        /* Кнопки управления (запустить/остановить) — шрифт Inter/Roboto */
        .btn {
            background: rgba(0,30,40,0.8);
            border: 1px solid #0fa;
            color: #0fa;
            padding: 12px;
            border-radius: 20px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.15s;
            text-align: center;
            font-family: 'Inter', 'Roboto', 'Segoe UI', sans-serif;
            letter-spacing: 0.5px;
            box-shadow: 0 0 3px rgba(0,255,170,0.3);
        }
        .btn:hover {
            background: #0fa;
            color: #0a0c12;
            box-shadow: 0 0 8px #0fa;
        }
        .btn-primary { background: #0fa; color: #0a0c12; border: none; }
        .btn-danger { border-color: #f55; color: #f55; }
        .btn-danger:hover { background: #f55; color: #0a0c12; }

        .right-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
            min-width: 0;
        }
        .log-container {
            background: rgba(8,12,20,0.8);
            border-radius: 28px;
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(0,200,150,0.3);
            min-height: 0;
        }
        .log-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(0,255,170,0.3);
            flex-shrink: 0;
            font-family: 'Orbitron', monospace;
        }
        /* Кнопка ОЧИСТИТЬ — шрифт Inter/Roboto */
        #clearLog {
            font-family: 'Inter', 'Roboto', monospace;
            font-weight: 500;
            cursor: pointer;
            font-size: 12px;
            color: #0fa;
        }
        .log-list {
            flex: 1;
            overflow-y: auto;
            font-family: 'Fira Code', 'Roboto', monospace;
            font-size: 12px;
            min-height: 0;
        }
        .log-entry {
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .log-entry:hover {
            background: rgba(0,255,170,0.05);
        }
        .log-time { color: #6c8a9e; min-width: 70px; }
        .log-message { color: #ccc; word-break: break-word; flex: 1; }
        .log-message.user { color: #0fa; font-weight: bold; }
        .log-message.jarvis { color: #f5a97f; }

        .quick-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            background: rgba(8,12,20,0.8);
            border-radius: 28px;
            padding: 15px;
            border: 1px solid rgba(0,200,150,0.3);
            flex-shrink: 0;
        }
        .quick-btn {
            background: #0f2630;
            border: none;
            padding: 8px 16px;
            border-radius: 40px;
            color: #0fa;
            cursor: pointer;
            transition: 0.15s;
            font-size: 13px;
            font-weight: 500;
            font-family: 'Exo 2', 'Orbitron', sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .quick-btn:hover {
            background: #0fa;
            color: #0a0c12;
            transform: translateY(-1px);
        }

        @media (max-width: 900px) {
            .grid { flex-direction: column; }
            .left-panel { width: 100%; flex-direction: row; flex-wrap: wrap; gap: 15px; }
            .left-panel > * { flex: 1; min-width: 200px; }
            .right-panel { width: 100%; }
            .quick-buttons { justify-content: center; }
        }
        @media (max-width: 600px) {
            .title-bar h1 { font-size: 24px; }
            .title-bar span { font-size: 10px; }
            .status-text { font-size: 18px; }
            .mic-icon { font-size: 60px; }
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #1a2a30; border-radius: 5px; }
        ::-webkit-scrollbar-thumb { background: #0fa; border-radius: 5px; }
    </style>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
<div class="bg-gradient"></div>
<div class="grid-lines"></div>
<div class="app">
    <div class="title-bar">
        <h1><i class="fas fa-microchip"></i> J.A.R.V.I.S.</h1>
        <span><i class="fas fa-microphone-alt"></i> ГОЛОСОВОЙ АССИСТЕНТ | <i class="fas fa-brain"></i> ИИ РЕЖИМ</span>
    </div>
    <div class="grid">
        <div class="left-panel">
            <div class="status-card">
                <div class="mic-icon" id="micIcon"><i class="fas fa-microphone"></i></div>
                <div class="status-text" id="statusText">НЕ АКТИВЕН</div>
                <div class="status-text" id="aiModeText" style="font-size:16px; margin-top:8px;"></div>
            </div>
            <div class="sys-card">
                <div class="sys-title"><i class="fas fa-desktop"></i> СИСТЕМА</div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-microchip"></i> CPU</span><span class="sys-value" id="cpu">--%</span></div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-memory"></i> RAM</span><span class="sys-value" id="ram">--%</span></div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-battery-full"></i> BATTERY</span><span class="sys-value" id="battery">--%</span></div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-hdd"></i> DISK</span><span class="sys-value" id="disk">--%</span></div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-network-wired"></i> IP</span><span class="sys-value" id="ip">--</span></div>
                <div class="sys-item"><span class="sys-label"><i class="fas fa-user"></i> USER</span><span class="sys-value" id="user">--</span></div>
            </div>
            <div class="btn btn-primary" id="startListeningBtn"><i class="fas fa-play"></i> ЗАПУСТИТЬ ПРОСЛУШИВАНИЕ</div>
            <div class="btn btn-danger" id="stopListeningBtn"><i class="fas fa-stop"></i> ОСТАНОВИТЬ ПРОСЛУШИВАНИЕ</div>
        </div>
        <div class="right-panel">
            <div class="log-container">
                <div class="log-header">
                    <span><i class="fas fa-terminal"></i> ЛОГ КОМАНД</span>
                    <span id="clearLog"><i class="fas fa-trash-alt"></i> ОЧИСТИТЬ</span>
                </div>
                <div class="log-list" id="logList">
                    <div class="log-entry"><span class="log-time">--:--:--</span><span class="log-message jarvis"><i class="fas fa-check-circle"></i> J.A.R.V.I.S. готов</span></div>
                </div>
            </div>
            <div class="quick-buttons">
                <div class="quick-btn" data-cmd="громче"><i class="fas fa-volume-up"></i> Громче</div>
                <div class="quick-btn" data-cmd="тише"><i class="fas fa-volume-down"></i> Тише</div>
                <div class="quick-btn" data-cmd="погода"><i class="fas fa-cloud-sun"></i> Погода</div>
                <div class="quick-btn" data-cmd="новости"><i class="fas fa-newspaper"></i> Новости</div>
                <div class="quick-btn" data-cmd="скриншот"><i class="fas fa-camera"></i> Скриншот</div>
                <div class="quick-btn" data-cmd="открой блокнот"><i class="fas fa-edit"></i> Блокнот</div>
                <div class="quick-btn" data-cmd="открой ютуб"><i class="fab fa-youtube"></i> YouTube</div>
                <div class="quick-btn" data-cmd="открой вк"><i class="fab fa-vk"></i> ВК</div>
                <div class="quick-btn" data-cmd="включи ии"><i class="fas fa-brain"></i> ИИ вкл</div>
                <div class="quick-btn" data-cmd="выключи ии"><i class="fas fa-microchip"></i> ИИ выкл</div>
                <div class="quick-btn" data-cmd="выключи компьютер"><i class="fas fa-power-off"></i> Выкл ПК</div>
                <div class="quick-btn" data-cmd="курс доллара"><i class="fas fa-dollar-sign"></i> Курс USD</div>
                <div class="quick-btn" data-cmd="таймер на 10"><i class="fas fa-hourglass-half"></i> Таймер 10с</div>
                <div class="quick-btn" data-cmd="цитата"><i class="fas fa-quote-right"></i> Цитата</div>
            </div>
        </div>
    </div>
</div>
<script>
    let jarvis = null;
    const micIcon = document.getElementById('micIcon');
    const statusText = document.getElementById('statusText');
    const aiModeText = document.getElementById('aiModeText');
    const logList = document.getElementById('logList');

    function addLog(message, sender = 'jarvis') {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        const icon = sender === 'user' ? '<i class="fas fa-microphone-alt"></i> ' : '<i class="fas fa-robot"></i> ';
        entry.innerHTML = `<span class="log-time">${timeStr}</span><span class="log-message ${sender}">${icon}${message}</span>`;
        logList.appendChild(entry);
        entry.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    document.getElementById('clearLog').onclick = () => { 
        logList.innerHTML = ''; 
        addLog('Лог очищен', 'jarvis'); 
    };

    async function executeCommand(cmd) {
        addLog(cmd, 'user');
        if (jarvis) {
            try {
                await jarvis.execute_command(cmd);
            } catch(e) { 
                addLog('Ошибка: ' + e, 'jarvis'); 
            }
        } else {
            addLog('Мост не готов', 'jarvis');
        }
    }

    async function updateSystemInfo() {
        if (jarvis) {
            try {
                const info = await jarvis.get_system_info();
                document.getElementById('cpu').innerHTML = info.cpu + '%';
                document.getElementById('ram').innerHTML = info.ram + '%';
                document.getElementById('battery').innerHTML = info.battery + '%';
                document.getElementById('disk').innerHTML = info.disk + '%';
                document.getElementById('ip').innerHTML = info.ip;
                document.getElementById('user').innerHTML = info.user;
            } catch(e) {}
        }
    }

    document.getElementById('startListeningBtn').onclick = () => { 
        if(jarvis) jarvis.start_listening(); 
        else addLog('Мост не готов', 'jarvis'); 
    };
    document.getElementById('stopListeningBtn').onclick = () => { 
        if(jarvis) jarvis.stop_listening(); 
        else addLog('Мост не готов', 'jarvis'); 
    };
    document.querySelectorAll('.quick-btn').forEach(btn => btn.onclick = () => executeCommand(btn.getAttribute('data-cmd')));

    window.updateStatus = function(status, aiMode) {
        statusText.innerText = status.toUpperCase();
        if (status.includes('АКТИВЕН') || status.includes('Слушаю')) {
            statusText.className = 'status-text status-active';
            micIcon.classList.add('listening');
        } else {
            statusText.className = 'status-text status-inactive';
            micIcon.classList.remove('listening');
        }
        aiModeText.innerText = aiMode ? '🤖 ИИ РЕЖИМ АКТИВЕН' : '⚙️ ОБЫЧНЫЙ РЕЖИМ';
        aiModeText.style.color = aiMode ? '#0fa' : '#8aa';
        addLog(`Статус: ${status}`, 'jarvis');
    };
    window.addLogFromPython = function(message) { addLog(message, 'jarvis'); };

    document.addEventListener('DOMContentLoaded', () => {
        new QWebChannel(qt.webChannelTransport, (channel) => { 
            jarvis = channel.objects.jarvis; 
            console.log("QWebChannel ready");
            addLog('Интерфейс загружен. Нажмите "ЗАПУСТИТЬ ПРОСЛУШИВАНИЕ".', 'jarvis');
        });
    });
    setInterval(updateSystemInfo, 8000);
    updateSystemInfo();
</script>
</body>
</html>
"""


class WebWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S.")
        self.setGeometry(100, 100, 1300, 850)
        self.setMinimumSize(1000, 650)
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        self.channel = QWebChannel()
        self.api = JarvisAPI(self)
        self.channel.registerObject("jarvis", self.api)
        self.browser.page().setWebChannel(self.channel)
        self.browser.setHtml(HTML)
        self.api.logMessage.connect(self._on_log_message)
        self.api.statusChanged.connect(self._on_status_changed)
        self.api.aiModeChanged.connect(self._on_ai_mode_changed)

    def _on_log_message(self, msg):
        safe = msg.replace("'", "\\'").replace('"', '\\"')
        self.browser.page().runJavaScript(f"window.addLogFromPython('{safe}');")
    def _on_status_changed(self, status, ai_mode):
        safe = status.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.updateStatus('{safe}', {str(ai_mode).lower()});")
    def _on_ai_mode_changed(self, mode):
        self.browser.page().runJavaScript(f"window.updateStatus('ИИ режим: {'ВКЛ' if mode else 'ВЫКЛ'}', {str(mode).lower()});")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebWindow()
    window.show()
    sys.exit(app.exec())