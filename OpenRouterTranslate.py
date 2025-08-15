# Implementation of OpenRouterTranslate using OpenRouter API with Gemma 3 model

import os
import openai
from dotenv import load_dotenv

class OpenRouterTranslate:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.initialized = False
        
        if self.api_key:
            # Configure the OpenAI client to use OpenRouter
            self.client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key
            )
            self.initialized = True
            print("OpenRouterTranslate initialized successfully")
        else:
            print("Warning: OpenRouter API key not provided")
    
    def translate(self, text, source_language, target_language):
        """Translate text using OpenRouter's Gemma model"""
        if not self.initialized:
            print("OpenRouterTranslate not initialized properly")
            return self._mock_translate(text, target_language)
        
        try:
            # Create a prompt for translation
            prompt = f"Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else:\n\n{text}"
            
            # Call OpenRouter API using OpenAI client
            response = self.client.chat.completions.create(
                model="google/gemma-3-27b-it-free",  # Using Gemma 3 27b it free model
                messages=[
                    {"role": "system", "content": "You are a helpful translation assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more accurate translations
            )
            
            # Extract the translated text from the response
            translated_text = response.choices[0].message.content.strip()
            return translated_text
            
        except Exception as e:
            print(f"Translation error: {e}")
            # Fall back to mock translation if API call fails
            return self._mock_translate(text, target_language)
    
    def _mock_translate(self, text, target_language):
        """Mock translation function as fallback"""
        print(f"Using mock translation for {target_language}: {text}")
        
        # For demonstration, we'll add a prefix to show it was "translated"
        if target_language == "hi":
            return f"[हिंदी अनुवाद] {text}"
        elif target_language == "ta":
            return f"[தமிழ் மொழிபெயர்ப்பு] {text}"
        elif target_language == "te":
            return f"[తెలుగు అనువాదం] {text}"
        elif target_language == "bn":
            return f"[বাংলা অনুবাদ] {text}"
        elif target_language == "mr":
            return f"[मराठी अनुवाद] {text}"
        elif target_language == "gu":
            return f"[ગુજરાતી અનુવાદ] {text}"
        elif target_language == "kn":
            return f"[ಕನ್ನಡ ಅನುವಾದ] {text}"
        elif target_language == "ml":
            return f"[മലയാളം വിവർത്തനം] {text}"
        elif target_language == "pa":
            return f"[ਪੰਜਾਬੀ ਅਨੁਵਾਦ] {text}"
        else:
            return text
    
    def detect_language(self, text):
        """Language detection"""
        if not self.initialized:
            return "en"
            
        try:
            # Use OpenRouter to detect language
            prompt = f"Detect the language of the following text and respond with only the ISO 639-1 language code (e.g., 'en', 'hi', 'ta'):\n\n{text}"
            
            response = self.client.chat.completions.create(
                model="google/gemma-3-27b-it-free",
                messages=[
                    {"role": "system", "content": "You are a language detection assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            
            detected_lang = response.choices[0].message.content.strip().lower()
            # Extract just the language code if there's additional text
            if len(detected_lang) > 2:
                for word in detected_lang.split():
                    if len(word) == 2:
                        detected_lang = word
                        break
                else:
                    detected_lang = "en"  # Default to English if no valid code found
            
            return detected_lang
            
        except Exception as e:
            print(f"Language detection error: {e}")
            return "en"  # Default to English on error