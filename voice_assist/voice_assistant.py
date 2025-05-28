#!/usr/bin/env python3
"""
Integrated Voice Assistant - "Ziggy"
Combines all tested components into a complete voice assistant

Features:
- Custom "ziggy" wake word detection using Vosk
- Smart query routing (local functions vs AI)
- GPU-accelerated AI responses via msty.app
- espeak text-to-speech output
- Auto-start capability with welcome message
- "take a break" command to gracefully shutdown
- Local-first privacy protection

Usage: python3 voice_assistant.py
Dependencies: vosk, pyaudio, requests
"""

import json
import re
import subprocess
import time
import tempfile
import signal
import sys
from datetime import datetime
from pathlib import Path

import requests
import vosk
import pyaudio
import wave


class VoiceAssistant:
    def __init__(self):
        # Configuration
        self.msty_url = "http://localhost:10000"
        self.wake_word = "ziggy"
        self.shutdown_phrase = "take a break"
        self.is_listening = True
        self.is_processing = False

        # Audio configuration
        self.sample_rate = 16000
        self.chunk_size = 4000
        self.channels = 1
        self.format = pyaudio.paInt16

        # Initialize components
        self.audio = None
        self.vosk_model = None
        self.default_model = None
        self.setup_successful = False

        print("🤖 Initializing Ziggy Voice Assistant...")
        self.setup_components()

    def setup_components(self):
        """Initialize all voice assistant components"""
        try:
            # Initialize audio system
            self.audio = pyaudio.PyAudio()
            print("✅ Audio system initialized")

            # Load Vosk model
            model_paths = [
                Path("vosk-model-small-en-us-0.15"),
                Path("vosk-model-en-us-0.22"),
                Path("vosk-model-en-us-0.22-lgraph"),
            ]

            model_path = None
            for path in model_paths:
                if path.exists():
                    model_path = str(path)
                    break

            if not model_path:
                print("❌ No Vosk model found. Please download:")
                print("wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
                print("unzip vosk-model-small-en-us-0.15.zip")
                return

            self.vosk_model = vosk.Model(model_path)
            print("✅ Speech recognition model loaded")

            # Test AI connection
            try:
                response = requests.get(f"{self.msty_url}/v1/models", timeout=5)
                if response.status_code == 200:
                    models_data = response.json()
                    if 'data' in models_data and models_data['data']:
                        self.default_model = models_data['data'][0]['id']  # Use first available
                        print(f"✅ AI backend connected (model: {self.default_model})")
                    else:
                        self.default_model = "llama3.2:latest"  # Fallback
                        print("✅ AI backend connected (using fallback model)")
                else:
                    print("❌ AI backend not responding correctly")
                    return
            except Exception as e:
                print(f"❌ Cannot connect to AI backend: {e}")
                return

            # Test text-to-speech
            try:
                result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Text-to-speech system ready")
                else:
                    print("❌ espeak not found - install with: sudo apt install espeak")
                    return
            except Exception as e:
                print(f"❌ Text-to-speech error: {e}")
                return

            self.setup_successful = True
            print("🎉 All systems ready!")

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            self.setup_successful = False

    def speak(self, text):
        """Convert text to speech using espeak"""
        try:
            print(f"🗣️ Speaking: {text}")
            subprocess.run([
                'espeak',
                '-s', '150',  # Speed (words per minute)
                '-v', 'en',  # Voice (English)
                text
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Speech error: {e}")

    def get_time(self):
        """Get current time - local function"""
        now = datetime.now()
        return f"The time is {now.strftime('%I:%M %p')}"

    def get_date(self):
        """Get current date - local function"""
        now = datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}"

    def handle_conversion(self, text):
        """Handle unit conversions - local function"""
        text_lower = text.lower()

        # Temperature conversion
        if 'celsius' in text_lower and 'fahrenheit' in text_lower:
            numbers = re.findall(r'-?\d+\.?\d*', text)
            if numbers:
                if 'celsius' in text_lower.split('fahrenheit')[0]:
                    # Celsius to Fahrenheit
                    celsius = float(numbers[0])
                    fahrenheit = (celsius * 9 / 5) + 32
                    return f"{celsius} degrees Celsius is {fahrenheit:.1f} degrees Fahrenheit"
                else:
                    # Fahrenheit to Celsius
                    fahrenheit = float(numbers[0])
                    celsius = (fahrenheit - 32) * 5 / 9
                    return f"{fahrenheit} degrees Fahrenheit is {celsius:.1f} degrees Celsius"

        # Distance conversion
        if 'feet' in text_lower and 'meters' in text_lower:
            numbers = re.findall(r'-?\d+\.?\d*', text)
            if numbers:
                if 'feet' in text_lower.split('meters')[0]:
                    # Feet to meters
                    feet = float(numbers[0])
                    meters = feet * 0.3048
                    return f"{feet} feet is {meters:.2f} meters"
                else:
                    # Meters to feet
                    meters = float(numbers[0])
                    feet = meters / 0.3048
                    return f"{meters} meters is {feet:.2f} feet"

        return None  # Conversion not handled locally

    def request_online_permission(self, query_type="search"):
        """Request explicit permission before any online activity"""
        permission_text = f"I cannot answer that from my local resources. Do you want me to check online?"
        self.speak(permission_text)
        print(f"🌐 Requesting online permission for: {query_type}")

        # Record user response
        response_audio = self.record_command(duration=3)
        if response_audio:
            response_text = self.speech_to_text(response_audio)
            response_lower = response_text.lower().strip()

            # Check for affirmative responses
            affirmative_words = ['yes', 'yeah', 'yep', 'okay', 'ok', 'sure', 'go ahead', 'please']
            negative_words = ['no', 'nope', 'don\'t', 'stop', 'cancel', 'nevermind']

            if any(word in response_lower for word in affirmative_words):
                print(f"✅ Online permission granted")
                return True
            elif any(word in response_lower for word in negative_words):
                print(f"❌ Online permission denied")
                return False
            else:
                # Unclear response - err on side of caution
                print(f"⚠️ Unclear response - defaulting to no online access")
                return False
        else:
            print(f"❌ No response - defaulting to no online access")
            return False

    def web_search(self, query):
        """Launch web search - requires explicit permission"""
        # Request permission first
        if not self.request_online_permission("web search"):
            return "Okay, staying local. Is there anything else I can help you with?"

        try:
            subprocess.run(['firefox', f'https://duckduckgo.com/?q={query}'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening web search for {query}"
        except:
            return "Could not open web browser"

    def query_ai_local_only(self, text):
        """Send query to local AI with explicit local-only instruction"""
        try:
            payload = {
                "model": self.default_model,
                "messages": [
                    {"role": "system",
                     "content": "You are a local AI assistant. Answer questions using only your training data. If a question requires current information, real-time data, or internet searches, respond with exactly: 'I need online resources to answer that properly.'"},
                    {"role": "user", "content": f"Please provide a brief, spoken response to: {text}"}
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }

            response = requests.post(
                f"{self.msty_url}/v1/chat/completions",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()

                # Check if AI indicates it needs online resources
                if "I need online resources" in ai_response:
                    if not self.request_online_permission("AI research with online context"):
                        return "Okay, I'll stick to what I know locally. Is there anything else I can help you with from my local knowledge?"

                    # Permission granted - send query without local-only restriction
                    return self.query_ai_unrestricted(text)

                return ai_response
            else:
                return "Sorry, I couldn't process that request"

        except Exception as e:
            print(f"AI query error: {e}")
            return "Sorry, there was an error processing your request"

    def query_ai_unrestricted(self, text):
        """Send query to AI without local-only restrictions (after permission granted)"""
        try:
            payload = {
                "model": self.default_model,
                "messages": [
                    {"role": "user", "content": f"Please provide a brief, spoken response to: {text}"}
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }

            response = requests.post(
                f"{self.msty_url}/v1/chat/completions",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return "Sorry, I couldn't process that request"

        except Exception as e:
            print(f"AI query error: {e}")
            return "Sorry, there was an error processing your request"

    def route_query(self, text):
        """Route query to appropriate handler"""
        text_lower = text.lower().strip()

        # Check for shutdown command
        if self.shutdown_phrase in text_lower:
            return "shutdown", "Okay, bye!"

        # Time queries
        if any(word in text_lower for word in ['time', 'clock', "what time"]):
            return "local", self.get_time()

        # Date queries
        if any(word in text_lower for word in ['date', 'today', "what day"]):
            return "local", self.get_date()

        # Unit conversions
        if 'convert' in text_lower or any(unit in text_lower for unit in [
            'celsius', 'fahrenheit', 'meters', 'feet', 'pounds', 'kilograms'
        ]):
            conversion_result = self.handle_conversion(text)
            if conversion_result:
                return "local", conversion_result

        # Web search
        if text_lower.startswith('search') or 'look up' in text_lower:
            query = text_lower.replace('search', '').replace('look up', '').strip()
            return "local", self.web_search(query)

        # Send to AI for complex queries (local-first with permission model)
        return "ai", self.query_ai_local_only(text)

    def record_command(self, duration=5):
        """Record audio command after wake word detection"""
        try:
            print(f"🎤 Recording command for {duration} seconds...")

            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            frames = []
            for _ in range(0, int(self.sample_rate / self.chunk_size * duration)):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)

            stream.close()
            return b''.join(frames)

        except Exception as e:
            print(f"Recording error: {e}")
            return None

    def speech_to_text(self, audio_data):
        """Convert audio data to text using Vosk"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_filename = temp_file.name

            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)

            # Transcribe with Vosk
            recognizer = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
            results = []

            with wave.open(temp_filename, 'rb') as wf:
                while True:
                    data = wf.readframes(self.chunk_size)
                    if len(data) == 0:
                        break
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        if result.get('text'):
                            results.append(result['text'])

            # Get final result
            final_result = json.loads(recognizer.FinalResult())
            if final_result.get('text'):
                results.append(final_result['text'])

            # Cleanup
            Path(temp_filename).unlink(missing_ok=True)

            return ' '.join(results).strip()

        except Exception as e:
            print(f"Speech recognition error: {e}")
            return ""

    def listen_for_wake_word(self):
        """Continuously listen for the wake word 'ziggy'"""
        try:
            recognizer = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)

            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            print(f"👂 Listening for wake word '{self.wake_word}'...")

            while self.is_listening:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        if result.get('text'):
                            transcript = result['text'].lower().strip()

                            # Check for wake word
                            if self.wake_word in transcript:
                                print(f"🎉 Wake word detected: '{transcript}'")
                                stream.close()
                                return True  # Wake word found

                            # Check for shutdown command
                            if self.shutdown_phrase in transcript:
                                print(f"🛑 Shutdown command detected: '{transcript}'")
                                stream.close()
                                return "shutdown"

                except Exception as e:
                    if self.is_listening:  # Only print error if we're still supposed to be listening
                        print(f"Listen error: {e}")
                        time.sleep(0.1)

            stream.close()
            return False

        except Exception as e:
            print(f"Wake word detection error: {e}")
            return False

    def handle_voice_command(self):
        """Handle complete voice interaction after wake word"""
        try:
            self.is_processing = True
            self.speak("Yes?")  # Acknowledge wake word

            # Record the user's command
            audio_data = self.record_command()
            if not audio_data:
                self.speak("I didn't hear anything")
                return

            # Convert speech to text
            command_text = self.speech_to_text(audio_data)
            if not command_text:
                self.speak("I couldn't understand that")
                return

            print(f"📝 Command: '{command_text}'")

            # Route and process the command
            route_type, response = self.route_query(command_text)

            if route_type == "shutdown":
                self.speak(response)
                self.shutdown()
                return

            # Speak the response
            self.speak(response)
            print(f"✅ Response delivered")

        except Exception as e:
            print(f"Command handling error: {e}")
            self.speak("Sorry, I had trouble processing that")
        finally:
            self.is_processing = False

    def startup_message(self):
        """Play welcome message on startup"""
        welcome_msg = "Welcome. Ziggy is ready to assist you."
        print(f"🤖 {welcome_msg}")
        self.speak(welcome_msg)

    def shutdown(self):
        """Gracefully shutdown the voice assistant"""
        print("🛑 Shutting down Ziggy...")
        self.is_listening = False
        if self.audio:
            self.audio.terminate()
        print("👋 Goodbye!")
        sys.exit(0)

    def run(self):
        """Main run loop for the voice assistant"""
        if not self.setup_successful:
            print("❌ Setup failed - cannot start voice assistant")
            return

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

        # Play startup message
        self.startup_message()

        print(f"\n🎯 Voice Assistant Active")
        print(f"Wake word: '{self.wake_word}'")
        print(f"Shutdown: '{self.shutdown_phrase}'")
        print(f"Press Ctrl+C to stop")
        print("-" * 50)

        try:
            while self.is_listening:
                # Listen for wake word
                wake_result = self.listen_for_wake_word()

                if wake_result == "shutdown":
                    self.speak("Okay, bye!")
                    self.shutdown()
                elif wake_result == True:
                    # Wake word detected - handle command
                    self.handle_voice_command()
                elif not self.is_listening:
                    # Shutdown requested
                    break

                # Brief pause before resuming listening
                if self.is_listening:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"Main loop error: {e}")
            self.shutdown()


def main():
    print("🤖 Ziggy Voice Assistant")
    print("Local-first AI assistant with privacy protection")
    print("=" * 50)

    # Create and run the voice assistant
    try:
        assistant = VoiceAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()