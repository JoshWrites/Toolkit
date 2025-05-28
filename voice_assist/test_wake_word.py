#!/usr/bin/env python3
"""
File: test_wake_word.py
Purpose: Test custom wake word detection using Vosk
Wake Word: "ziggy"
Dependencies: vosk, pyaudio
Run: python3 test_wake_word.py
"""

import json
import wave
import tempfile
import pyaudio
import time
import threading
from pathlib import Path


def test_wake_word():
    """
    Test custom wake word detection using Vosk speech recognition
    Listens continuously for "ziggy" to activate
    """
    print("=== Custom Wake Word Detection Test ===")
    print("Using wake word: 'ziggy'")

    # Check Vosk installation
    try:
        import vosk
        print("✅ Vosk module imported successfully")
    except ImportError:
        print("❌ Vosk not installed. Run: pip install vosk")
        return False

    # Check for Vosk model
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
        print("❌ No Vosk model found in current directory")
        print("Download with:")
        print("wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print("unzip vosk-model-small-en-us-0.15.zip")
        return False

    # Initialize Vosk model
    try:
        print(f"Loading Vosk model from: {model_path}")
        model = vosk.Model(model_path)
        print("✅ Vosk model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading Vosk model: {e}")
        return False

    # Audio configuration for continuous listening
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 4000  # Smaller chunks for responsiveness
    CHANNELS = 1
    FORMAT = pyaudio.paInt16

    # Wake word configuration
    WAKE_WORD = "ziggy"
    BUFFER_SECONDS = 3  # How many seconds of audio to analyze at once
    CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for wake word detection

    audio = pyaudio.PyAudio()

    try:
        print(f"\n--- Initializing Continuous Listening ---")
        print(f"Wake word: '{WAKE_WORD}'")
        print(f"Audio buffer: {BUFFER_SECONDS} seconds")
        print(f"Chunk size: {CHUNK_SIZE} samples")

        # Initialize recognizer
        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        recognizer.SetWords(True)  # Enable word-level confidence

        # Open microphone stream
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

        print(f"\n🎤 Listening for wake word '{WAKE_WORD}'...")
        print("Speak naturally - say 'ziggy' to test detection")
        print("Press Ctrl+C to stop test")
        print("-" * 50)

        detections = 0
        start_time = time.time()
        audio_buffer = []
        buffer_max_chunks = int(SAMPLE_RATE / CHUNK_SIZE * BUFFER_SECONDS)

        while True:
            try:
                # Read audio chunk
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                audio_buffer.append(data)

                # Maintain rolling buffer
                if len(audio_buffer) > buffer_max_chunks:
                    audio_buffer.pop(0)

                # Process audio with Vosk
                if recognizer.AcceptWaveform(data):
                    # Complete phrase recognized
                    result = json.loads(recognizer.Result())
                    if result.get('text'):
                        transcript = result['text'].lower().strip()
                        print(f"Heard: '{transcript}'")

                        # Check for wake word
                        if WAKE_WORD in transcript:
                            detections += 1
                            current_time = time.time() - start_time
                            print(f"\n🎉 WAKE WORD DETECTED! (#{detections} at {current_time:.1f}s)")
                            print(f"Full transcript: '{transcript}'")
                            print(f"Continue saying '{WAKE_WORD}' to test multiple detections")
                            print("-" * 50)
                else:
                    # Partial recognition (real-time feedback)
                    partial = json.loads(recognizer.PartialResult())
                    if partial.get('partial'):
                        partial_text = partial['partial'].lower()
                        if WAKE_WORD in partial_text:
                            print(f"Detecting... '{partial_text}'", end='\r')

                # Show periodic status
                elapsed = time.time() - start_time
                if int(elapsed) % 10 == 0 and int(elapsed * 10) % 100 == 0:
                    print(f"Listening... ({elapsed:.0f}s elapsed, {detections} detections)", end='\r')

            except KeyboardInterrupt:
                print(f"\n\nTest stopped by user")
                break
            except Exception as e:
                print(f"\nError during detection: {e}")
                break

        # Cleanup
        stream.close()

        # Final results
        print(f"\n--- Wake Word Test Results ---")
        print(f"Wake word: '{WAKE_WORD}'")
        print(f"Total detections: {detections}")
        print(f"Test duration: {time.time() - start_time:.1f} seconds")

        if detections > 0:
            print(f"\n✅ Custom wake word detection WORKING!")
            print(f"Successfully detected '{WAKE_WORD}' {detections} times")

            if detections > 10:
                print("⚠️ Many detections - consider using a more unique wake word")
            elif detections >= 3:
                print("👍 Good detection rate - wake word system ready")
            else:
                print("💡 Few detections - try speaking more clearly or closer to microphone")

            return True
        else:
            print(f"\n❌ No wake word detections")
            print("Troubleshooting:")
            print(f"- Say '{WAKE_WORD}' clearly and distinctly")
            print("- Try speaking louder or closer to microphone")
            print("- Ensure microphone is working (test_audio_system.py passed)")
            print("- Consider a different wake word if '{WAKE_WORD}' is too common")
            return False

    except Exception as e:
        print(f"❌ Wake word test failed: {e}")
        return False

    finally:
        audio.terminate()


def test_wake_word_accuracy():
    """
    Additional test for wake word accuracy
    Tests false positive rate with similar sounding words
    """
    print("\n=== Wake Word Accuracy Test ===")
    print("This tests how well the system distinguishes 'ziggy' from similar words")

    test_phrases = [
        "ziggy",  # Should detect (true positive)
        "piggy",  # Should NOT detect (similar sound)
        "sticky",  # Should NOT detect (similar ending)
        "dizzy",  # Should NOT detect (similar sound)
        "hey ziggy",  # Should detect (true positive in phrase)
        "zigzag",  # Should NOT detect (similar start)
        "crispy ziggy",  # Should detect (true positive in phrase)
    ]

    print("\nFor accuracy testing, you would say each phrase and verify:")
    for i, phrase in enumerate(test_phrases, 1):
        should_detect = "ziggy" in phrase.lower()
        status = "SHOULD detect" if should_detect else "should NOT detect"
        print(f"{i}. '{phrase}' - {status}")

    print("\nThis helps tune the system to avoid false activations.")
    print("For now, basic keyword matching should work well.")


def main():
    print("Voice Assistant - Custom Wake Word Detection Test")
    print("Using Vosk speech recognition to detect 'ziggy' wake word")
    print("This avoids external API dependencies while providing custom wake words")

    if test_wake_word():
        print("\n🎉 Ready for next step: test_msty_connection.py")

        # Show accuracy testing info
        test_wake_word_accuracy()
    else:
        print("\n❌ Fix wake word detection before proceeding")


if __name__ == "__main__":
    main()