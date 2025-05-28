#!/usr/bin/env python3
"""
Voice Assistant - Modular Testing Suite
Build and test each component independently before integration

Test Order:
1. test_audio_system.py - Verify microphone and speakers work
2. test_speech_to_text.py - Test Vosk speech recognition
3. test_text_to_speech.py - Test TTS output
4. test_wake_word.py - Test Porcupine wake word detection
5. test_msty_connection.py - Test local AI connection
6. test_router.py - Test query routing logic
7. voice_assistant_integrated.py - Full integration

Usage: python3 test_<component>.py
"""

# ==============================================================================
# SCRIPT 2: test_speech_to_text.py
# Tests Vosk speech recognition
# ==============================================================================

"""
File: test_speech_to_text.py
Purpose: Test Vosk speech-to-text functionality
Dependencies: pip install vosk
Run: python3 test_speech_to_text.py
"""

import json
import wave
import tempfile
import pyaudio
from pathlib import Path


def download_vosk_model():
    """
    Check if Vosk model exists, provide download instructions if not
    """
    model_paths = [
        Path("vosk-model-small-en-us-0.15"),
        Path("vosk-model-en-us-0.22"),
        Path("vosk-model-en-us-0.22-lgraph"),
    ]

    for model_path in model_paths:
        if model_path.exists():
            print(f"Found Vosk model: {model_path}")
            return str(model_path)

    print("No Vosk model found. Please download one:")
    print("\nQuick setup (small model, ~50MB):")
    print("wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
    print("unzip vosk-model-small-en-us-0.15.zip")
    print("\nBetter accuracy (larger model, ~1.8GB):")
    print("wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip")
    print("unzip vosk-model-en-us-0.22.zip")

    return None


def test_speech_to_text():
    """
    Test Vosk speech recognition with recorded audio
    """
    print("=== Speech-to-Text Test ===")

    # Check for Vosk installation
    try:
        import vosk
        print("✅ Vosk module imported successfully")
    except ImportError:
        print("❌ Vosk not installed. Run: pip install vosk")
        return False

    # Check for model
    model_path = download_vosk_model()
    if not model_path:
        return False

    # Initialize Vosk model
    try:
        print(f"Loading Vosk model from: {model_path}")
        model = vosk.Model(model_path)
        print("✅ Vosk model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading Vosk model: {e}")
        print("Try re-downloading the model or check file permissions")
        return False

    # Audio configuration
    SAMPLE_RATE = 16000  # Vosk works best at 16kHz
    CHUNK_SIZE = 4000  # Vosk recommended chunk size
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    RECORD_SECONDS = 5

    audio = pyaudio.PyAudio()

    try:
        # Record test audio
        print(f"\n--- Recording for Speech Recognition ---")
        print(f"Recording for {RECORD_SECONDS} seconds...")
        print("Please say clearly: 'Hello computer, what time is it today?'")

        input("Press Enter when ready to record...")

        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

        frames = []
        for i in range(0, int(SAMPLE_RATE / CHUNK_SIZE * RECORD_SECONDS)):
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

            # Progress indicator
            if i % 5 == 0:
                progress = (i * CHUNK_SIZE / SAMPLE_RATE / RECORD_SECONDS) * 100
                print(f"Recording: {progress:.0f}%", end='\r')

        stream.close()
        print("\n✅ Recording completed")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_filename = temp_file.name

        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        # Test speech recognition
        print("\n--- Testing Speech Recognition ---")

        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.SetWords(True)  # Enable word-level timestamps

        results = []
        partial_results = []

        with wave.open(temp_filename, 'rb') as wf:
            while True:
                data = wf.readframes(CHUNK_SIZE)
                if len(data) == 0:
                    break

                if recognizer.AcceptWaveform(data):
                    # Complete phrase recognized
                    result = json.loads(recognizer.Result())
                    if result.get('text'):
                        results.append(result['text'])
                        print(f"Recognized: '{result['text']}'")
                else:
                    # Partial recognition (real-time feedback)
                    partial = json.loads(recognizer.PartialResult())
                    if partial.get('partial'):
                        partial_text = partial['partial']
                        if partial_text not in partial_results:
                            partial_results.append(partial_text)
                            print(f"Partial: '{partial_text}'")

        # Get final result
        final_result = json.loads(recognizer.FinalResult())
        if final_result.get('text'):
            results.append(final_result['text'])
            print(f"Final: '{final_result['text']}'")

        # Analysis
        full_transcript = ' '.join(results).strip()

        print(f"\n--- Speech Recognition Results ---")
        print(f"Full transcript: '{full_transcript}'")
        print(f"Number of recognized phrases: {len(results)}")
        print(f"Transcript length: {len(full_transcript)} characters")

        if not full_transcript:
            print("❌ No speech recognized!")
            print("Troubleshooting:")
            print("- Speak louder and more clearly")
            print("- Check microphone is working (run test_audio_system.py)")
            print("- Try a different Vosk model")
            print("- Reduce background noise")
            return False

        # Basic quality checks
        expected_words = ['hello', 'computer', 'time', 'today']
        recognized_words = full_transcript.lower().split()
        matches = sum(1 for word in expected_words if word in recognized_words)

        print(f"\n--- Quality Assessment ---")
        print(f"Expected words found: {matches}/{len(expected_words)}")
        print(f"Recognition accuracy estimate: {(matches / len(expected_words) * 100):.0f}%")

        if matches >= 2:  # At least half the words recognized
            print("✅ Speech recognition quality: GOOD")
        elif matches >= 1:
            print("⚠️ Speech recognition quality: FAIR")
            print("Consider using a larger/better Vosk model for improved accuracy")
        else:
            print("❌ Speech recognition quality: POOR")
            print("Try speaking more clearly or check audio setup")

        # Cleanup
        Path(temp_filename).unlink(missing_ok=True)

        print("\n✅ Speech-to-text test completed!")
        return True

    except Exception as e:
        print(f"❌ Error during speech recognition test: {e}")
        return False

    finally:
        audio.terminate()


def main():
    print("Voice Assistant - Speech-to-Text Test")
    print("This test verifies Vosk speech recognition works correctly")

    if not test_speech_to_text():
        print("\n❌ Fix speech recognition issues before proceeding")
    else:
        print("\n🎉 Ready for next step: test_text_to_speech.py")


if __name__ == "__main__":
    main()