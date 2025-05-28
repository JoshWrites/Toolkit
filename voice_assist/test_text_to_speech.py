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
# SCRIPT 3: test_text_to_speech.py
# Tests text-to-speech output
# ==============================================================================

"""
File: test_text_to_speech.py  
Purpose: Test text-to-speech functionality
Dependencies: espeak (system) or pip install piper-tts
Run: python3 test_text_to_speech.py
"""

import subprocess
import tempfile
import time
from pathlib import Path


def test_espeak():
    """
    Test espeak TTS (system package)
    Fast, lightweight, but basic voice quality
    """
    print("--- Testing espeak TTS ---")

    try:
        # Check if espeak is installed
        result = subprocess.run(['which', 'espeak'],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ espeak not found")
            print("Install with: sudo apt install espeak espeak-data")
            return False

        print("✅ espeak found")

        # Test basic speech
        test_phrases = [
            "Hello, this is a test of the text to speech system.",
            "The time is twelve thirty PM.",
            "Converting 32 degrees Celsius to Fahrenheit equals 89.6 degrees.",
            "I am your voice assistant, ready to help."
        ]

        for i, phrase in enumerate(test_phrases, 1):
            print(f"\nTest {i}: Speaking '{phrase}'")

            try:
                # Basic espeak command
                result = subprocess.run([
                    'espeak',
                    '-s', '150',  # Speed (words per minute)
                    '-v', 'en',  # Voice (English)
                    phrase
                ], capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    print(f"✅ Test {i} completed")
                    time.sleep(0.5)  # Brief pause between tests
                else:
                    print(f"❌ Test {i} failed: {result.stderr}")

            except subprocess.TimeoutExpired:
                print(f"❌ Test {i} timed out")
            except Exception as e:
                print(f"❌ Test {i} error: {e}")

        # Test different voices if available
        print("\n--- Testing espeak voices ---")
        try:
            voices_result = subprocess.run(['espeak', '--voices=en'],
                                           capture_output=True, text=True)
            if voices_result.returncode == 0:
                voices = voices_result.stdout.strip().split('\n')[1:]  # Skip header
                print(f"Available English voices: {len(voices)}")

                # Test a few different voices
                for voice_line in voices[:3]:  # Test first 3 voices
                    voice_parts = voice_line.split()
                    if len(voice_parts) >= 2:
                        voice_name = voice_parts[1]
                        print(f"Testing voice: {voice_name}")

                        subprocess.run([
                            'espeak', '-v', voice_name, '-s', '150',
                            f"This is voice {voice_name}"
                        ], capture_output=True, timeout=5)
                        time.sleep(0.3)
        except:
            print("Could not test multiple voices")

        return True

    except Exception as e:
        print(f"❌ espeak test failed: {e}")
        return False


def test_piper():
    """
    Test Piper TTS (pip package)
    Higher quality voice, but requires more resources
    """
    print("\n--- Testing Piper TTS ---")

    try:
        import piper
        print("✅ Piper module imported")

        # Note: Piper setup is more complex, requires voice models
        # For now, just verify the module can be imported
        print("⚠️ Piper TTS detected but not fully tested")
        print("Piper requires voice model downloads for full testing")
        print("Using espeak for now, can upgrade to Piper later")

        return True

    except ImportError:
        print("ℹ️ Piper TTS not installed (optional)")
        print("Install with: pip install piper-tts")
        print("Continuing with espeak...")
        return False


def test_text_to_speech():
    """
    Test available TTS options
    """
    print("=== Text-to-Speech Test ===")

    # Test espeak (primary option)
    espeak_works = test_espeak()

    # Test Piper (optional upgrade)
    piper_available = test_piper()

    if espeak_works:
        print("\n✅ Text-to-speech test PASSED!")
        print("espeak is working correctly for voice responses")
        if piper_available:
            print("Piper is also available for potential quality upgrade")
        return True
    else:
        print("\n❌ Text-to-speech test FAILED!")
        print("Voice assistant needs working TTS for audio responses")
        return False


def main():
    print("Voice Assistant - Text-to-Speech Test")
    print("This test verifies TTS works for voice responses")
    print("You should hear several test phrases spoken aloud")

    input("\nPress Enter to start TTS test (make sure speakers are on)...")

    if test_text_to_speech():
        print("\n🎉 Ready for next step: test_wake_word.py")
    else:
        print("\n❌ Fix TTS issues before proceeding")


if __name__ == "__main__":
    main()
