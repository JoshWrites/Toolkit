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
# SCRIPT 1: test_audio_system.py
# Tests basic audio input/output functionality
# ==============================================================================

"""
File: test_audio_system.py
Purpose: Verify microphone input and speaker output work correctly
Run: python3 test_audio_system.py
"""

import pyaudio
import wave
import tempfile
import time
from pathlib import Path


def test_audio_system():
    """
    Test microphone recording and playback
    This verifies your audio hardware is working before testing speech components
    """
    print("=== Audio System Test ===")
    print("This will test microphone recording and speaker playback")

    # Audio configuration - matches what we'll use in voice assistant
    SAMPLE_RATE = 16000  # Standard rate for speech recognition
    CHUNK_SIZE = 1024  # Buffer size for audio processing
    CHANNELS = 1  # Mono audio (speech recognition standard)
    FORMAT = pyaudio.paInt16  # 16-bit audio format
    RECORD_SECONDS = 3  # Test recording duration

    audio = pyaudio.PyAudio()

    try:
        # Step 1: List available audio devices for troubleshooting
        print("\n--- Available Audio Devices ---")
        device_count = audio.get_device_count()

        input_devices = []
        output_devices = []

        for i in range(device_count):
            try:
                device_info = audio.get_device_info_by_index(i)
                print(f"Device {i}: {device_info['name']}")
                print(f"  Max Input Channels: {device_info['maxInputChannels']}")
                print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
                print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")

                if device_info['maxInputChannels'] > 0:
                    input_devices.append(i)
                if device_info['maxOutputChannels'] > 0:
                    output_devices.append(i)

            except Exception as e:
                print(f"Error reading device {i}: {e}")

        print(f"\nFound {len(input_devices)} input devices and {len(output_devices)} output devices")

        if not input_devices:
            print("ERROR: No input devices found! Check microphone connection.")
            return False

        if not output_devices:
            print("ERROR: No output devices found! Check speaker connection.")
            return False

        # Step 2: Test microphone recording
        print(f"\n--- Testing Microphone Recording ---")
        print(f"Recording for {RECORD_SECONDS} seconds...")
        print("Speak now: 'Hello, this is a test'")

        try:
            # Open microphone stream
            input_stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=None  # Use default device
            )

            # Record audio data
            frames = []
            for i in range(0, int(SAMPLE_RATE / CHUNK_SIZE * RECORD_SECONDS)):
                try:
                    data = input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(data)

                    # Show progress
                    if i % 10 == 0:
                        progress = (i * CHUNK_SIZE / SAMPLE_RATE / RECORD_SECONDS) * 100
                        print(f"Recording: {progress:.0f}%", end='\r')

                except Exception as e:
                    print(f"\nError during recording: {e}")
                    input_stream.close()
                    return False

            input_stream.close()
            print("\nRecording completed successfully!")

        except Exception as e:
            print(f"Error opening microphone: {e}")
            print("Common fixes:")
            print("- Check microphone is connected and not muted")
            print("- Try: sudo usermod -a -G audio $USER (then logout/login)")
            print("- Install: sudo apt install portaudio19-dev")
            return False

        # Step 3: Save recorded audio to file
        print("\n--- Saving Audio File ---")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_filename = temp_file.name

            # Write WAV file
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(frames))

            # Check file size as basic validation
            file_size = Path(temp_filename).stat().st_size
            expected_size = SAMPLE_RATE * 2 * RECORD_SECONDS  # 16-bit = 2 bytes per sample

            print(f"Audio file saved: {temp_filename}")
            print(f"File size: {file_size} bytes (expected ~{expected_size})")

            if file_size < expected_size * 0.8:  # Allow 20% variance
                print("WARNING: Audio file smaller than expected - possible recording issue")

        except Exception as e:
            print(f"Error saving audio file: {e}")
            return False

        # Step 4: Test playback
        print("\n--- Testing Speaker Playback ---")
        print("Playing back recorded audio...")

        try:
            # Open and read the audio file
            with wave.open(temp_filename, 'rb') as wf:
                # Open speaker stream
                output_stream = audio.open(
                    format=audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )

                # Play audio in chunks
                chunk_data = wf.readframes(CHUNK_SIZE)
                while chunk_data:
                    output_stream.write(chunk_data)
                    chunk_data = wf.readframes(CHUNK_SIZE)

                output_stream.close()
                print("Playback completed!")

        except Exception as e:
            print(f"Error during playback: {e}")
            print("Common fixes:")
            print("- Check speakers/headphones are connected")
            print("- Check system volume is not muted")
            print("- Try: pulseaudio --check && pulseaudio --start")
            return False

        # Cleanup
        try:
            Path(temp_filename).unlink()
        except:
            pass

        print("\n✅ Audio system test PASSED!")
        print("Microphone recording and speaker playback both work correctly.")
        return True

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

    finally:
        audio.terminate()


def main():
    print("Voice Assistant - Audio System Test")
    print("This test verifies your microphone and speakers work correctly")
    print("You'll be asked to speak for 3 seconds, then hear it played back")

    input("\nPress Enter to start audio test...")

    success = test_audio_system()

    if success:
        print("\n🎉 Ready for next step: test_speech_to_text.py")
    else:
        print("\n❌ Fix audio issues before proceeding")
        print("Check the error messages above for specific troubleshooting steps")


if __name__ == "__main__":
    main()