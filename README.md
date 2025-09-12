# AI-powered Local Governance Assistant

A web-based AI chatbot for Indian citizens to access government services, file grievances, and get guidance on RTI, tax, or bill payments. The application features multilingual support through Bhashini AI and uses the Gemini API for intelligent responses.

## Features

- **AI-powered Assistance**: Get accurate information about municipal services, document requirements, and government processes
- **Multilingual Support**: Communicate in multiple Indian languages using Bhashini AI translation
- **Voice Interaction**: Speak to the assistant and receive voice responses
- **Grievance Filing**: Get guidance on filing complaints and tracking their status
- **RTI Assistance**: Learn how to file RTI applications and follow up on them
- **Modern UI**: Clean, responsive interface built with Tailwind CSS

## Pages

- **Home**: Main page with chatbot interface and feature highlights
- **About**: Information about the AI Governance Assistant and its capabilities
- **Services**: Details about various government services the assistant can help with
- **Contact**: Form to get in touch with support team and FAQ section

## Technical Stack

- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Backend**: Python with Flask
- **AI Services**: 
  - Gemini API for natural language understanding
  - Bhashini AI for multilingual translation
  - Speech recognition and text-to-speech capabilities

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Create a `.env` file in the root directory
   - Add the following variables:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     BHASHINI_API_KEY=your_bhashini_api_key_here
     BHASHINI_USER_ID=your_bhashini_user_id_here
     BHASHINI_PIPLELINE_ID=your_bhashini_pipeline_id_here
     FLASK_SECRET_KEY=your_secret_key_here
     ```

4. **Run the application**
   ```
   python app.py
   ```

5. **Access the website**
   - Open your browser and go to `http://localhost:5000`

## API Endpoints

- `/chat`: Send and receive chat messages
- `/speech_input`: Convert speech to text
- `/text_to_speech`: Convert text to speech
- `/get_languages`: Get list of supported languages

## Obtaining API Keys

- **Gemini API**: Sign up at [Google AI Studio](https://ai.google.dev/)
- **Bhashini AI**: Register at [Bhashini](https://bhashini.gov.in/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
