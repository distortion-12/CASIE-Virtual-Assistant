
import os
import json
import threading
import asyncio
import base64
from time import sleep
from random import choice
import pyautogui
import mtranslate as mt
import eel
import speech_recognition as sr
from dotenv import load_dotenv, set_key
from threading import Lock

# Import backend modules
from Backend.Extra import AnswerModifier, QueryModifier, LoadMessages, GuiMessagesConverter
from Backend.Automation import run_automation as Automation
from Backend.Automation import PROFESSIONAL_RESPONSES as professional_responses
from Backend.RSE import RealTimeChatBotAI
from Backend.Chatbot import ChatBotAI
from Backend.AutoModel import Model
from Backend.ChatGpt import ChatBotAI as ChatGptAI
from Backend.TTS import TTS, TextToAudioFile

# Load environment variables
load_dotenv()

# Global variables
state = 'Available...'
messages = LoadMessages()
WEBCAM = False
js_messageslist = []
working: list[threading.Thread] = []
InputLanguage = os.environ['InputLanguage']
Assistantname = os.environ['AssistantName']
Username = os.environ['NickName']
lock = Lock()

# Wake and sleep words
WAKE_WORD = "hi casie"
SLEEP_WORD = "go sleep casie"
recognizer = sr.Recognizer()


def UniversalTranslator(Text: str) -> str:
    return mt.translate(Text, 'en', 'auto').capitalize()

def MainExecution(Query: str):
    global WEBCAM, state
    Query = UniversalTranslator(Query) if 'en' not in InputLanguage.lower() else Query.capitalize()
    Query = QueryModifier(Query)

    if state != 'Available...':
        return
    state = 'Thinking...'
    Decision = Model(Query)

    try:
        if 'general' in Decision or 'realtime' in Decision:
            if Decision[0] == 'general':
                if WEBCAM:
                    python_call_to_capture()
                    sleep(0.5)
                    Answer = ChatGptAI(Query)
                else:
                    Answer = AnswerModifier(ChatBotAI(Query))
                state = 'Answering...'
                TTS(Answer)
            else:
                state = 'Searching...'
                Answer = AnswerModifier(RealTimeChatBotAI(Query))
                state = 'Answering...'
                TTS(Answer)
        elif 'open webcam' in Decision:
            python_call_to_start_video()
            print('Video Started')
            WEBCAM = True
        elif 'close webcam' in Decision:
            print('Video Stopped')
            python_call_to_stop_video()
            WEBCAM = False
        else:
            state = 'Automation...'
            asyncio.run(Automation(Decision, print))
            response = choice(professional_responses)
            state = 'Answering...'
            with open('ChatLog.json', 'w') as f:
                json.dump(messages + [{'role': 'assistant', 'content': response}], f, indent=4)
            TTS(response)
    finally:
        state = 'Listening...'


def listen():
    with sr.Microphone() as source:
        print("[Listening for wake/sleep words]...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio).lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""


async def wake_word_loop():
    global state
    active = False
    while True:
        phrase = listen()
        if not active and WAKE_WORD in phrase:
            active = True
            TTS("CASIE activated. How can I assist you?")
        elif active and SLEEP_WORD in phrase:
            active = False
            TTS("CASIE going to sleep. Say 'Hi CASIE' to wake me again.")
        elif active and phrase:
            js_mic(phrase)
        sleep(0.5)


@eel.expose
def js_messages():
    global messages, js_messageslist
    with lock:
        messages = LoadMessages()
    if js_messageslist != messages:
        new_messages = GuiMessagesConverter(messages[len(js_messageslist):])
        js_messageslist = messages
        return new_messages
    return []

@eel.expose
def js_state(stat=None):
    global state
    if stat:
        state = stat
    return state

@eel.expose
def js_mic(transcription):
    print(transcription)
    if not working or not working[0].is_alive():
        work = threading.Thread(target=MainExecution, args=(transcription,), daemon=True)
        work.start()
        working.append(work)

@eel.expose
def python_call_to_start_video():
    eel.startVideo()

@eel.expose
def python_call_to_stop_video():
    eel.stopVideo()

@eel.expose
def python_call_to_capture():
    eel.capture()

@eel.expose
def js_page(cpage=None):
    if cpage == 'home':
        eel.openHome()
    elif cpage == 'settings':
        eel.openSettings()

@eel.expose
def js_setvalues(GeminiApi, HuggingFaceApi, GroqApi, AssistantName, Username):
    if GeminiApi:
        set_key('.env', 'CohereAPI', GeminiApi)
    if HuggingFaceApi:
        set_key('.env', 'HuggingFaceAPI', HuggingFaceApi)
    if GroqApi:
        set_key('.env', 'GroqAPI', GroqApi)
    if AssistantName:
        set_key('.env', 'AssistantName', AssistantName)
    if Username:
        set_key('.env', 'NickName', Username)

@eel.expose
def setup():
    pyautogui.hotkey('win', 'up')

@eel.expose
def js_language():
    return InputLanguage

@eel.expose
def js_assistantname():
    return Assistantname

@eel.expose
def js_capture(image_data):
    image_bytes = base64.b64decode(image_data.split(',')[1])
    with open('capture.png', 'wb') as f:
        f.write(image_bytes)

# Initialize Eel and start the application
if __name__ == '__main__':
    eel.init('web')

    def start_gui():
        eel.start('spider.html', port=44445)

    def start_backend():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_all():
            await TextToAudioFile(f"Hello, I am {Assistantname}. Say '{WAKE_WORD}' to activate me.")
            await wake_word_loop()

        try:
            loop.run_until_complete(run_all())
        except Exception as e:
            print(f"[Startup Error] {e}")

    threading.Thread(target=start_gui, daemon=True).start()
    threading.Thread(target=start_backend, daemon=True).start()

    while True:
        sleep(1)
