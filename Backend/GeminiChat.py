import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
google_key = os.getenv('GoogleAPI')
genai.configure(api_key=google_key)
