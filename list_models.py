import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

genai.configure(api_key=os.getenv("AIzaSyDvt9OZQZLNtLv3U9mI_lj1GsqfI14lTtQ"))

print("Available models:")
for model in genai.list_models():
    print(f"  - {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"    Supported methods: {model.supported_generation_methods}")
