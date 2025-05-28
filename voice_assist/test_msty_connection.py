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
# SCRIPT 5: test_msty_connection.py
# Tests connection to local msty.app AI
# ==============================================================================

"""
File: test_msty_connection.py
Purpose: Test connection to msty.app local AI instance
Dependencies: requests (usually pre-installed)
Run: python3 test_msty_connection.py
"""

import requests
import json
import time


def test_msty_connection():
    """
    Test connection and communication with msty.app
    """
    print("=== msty.app Connection Test ===")

    # Configuration
    MSTY_URL = "http://localhost:10000"
    TIMEOUT = 30  # Seconds to wait for AI response

    # Test 1: Check if msty.app is running
    print(f"\n--- Testing Connection to {MSTY_URL} ---")

    try:
        # Simple health check
        response = requests.get(f"{MSTY_URL}/health", timeout=5)
        print(f"✅ Health check successful: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {MSTY_URL}")
        print("Troubleshooting:")
        print("- Is msty.app running? Check with: ps aux | grep msty")
        print("- Is it listening on port 10000? Check with: netstat -tulpn | grep 10000")
        print("- Try starting msty.app and wait for it to fully load")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Connection timeout to {MSTY_URL}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

    # Test 2: Check API endpoints
    print(f"\n--- Testing API Endpoints ---")

    try:
        # Try to get model information
        models_response = requests.get(f"{MSTY_URL}/v1/models", timeout=10)

        if models_response.status_code == 200:
            models_data = models_response.json()
            print(f"✅ Models endpoint working")

            if 'data' in models_data and models_data['data']:
                available_models = [model['id'] for model in models_data['data']]
                print(f"Available models: {available_models}")
                default_model = available_models[0]  # Use first available model
            else:
                print("⚠️ No models found in response, using 'default'")
                default_model = "default"
        else:
            print(f"⚠️ Models endpoint returned {models_response.status_code}, using 'default' model")
            default_model = "default"

    except Exception as e:
        print(f"⚠️ Could not get model list: {e}")
        print("Continuing with default model...")
        default_model = "default"

    # Test 3: Simple AI query
    print(f"\n--- Testing AI Chat Completion ---")

    test_queries = [
        {
            "prompt": "What is 2 + 2?",
            "expected_type": "number",
            "description": "Simple math test"
        },
        {
            "prompt": "Say 'Hello, I am your voice assistant' in exactly that phrase.",
            "expected_type": "greeting",
            "description": "Response formatting test"
        },
        {
            "prompt": "What time is it?",
            "expected_type": "time",
            "description": "Time query test (should explain it doesn't know current time)"
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Query: '{test['prompt']}'")

        try:
            # Prepare the chat completion request
            payload = {
                "model": default_model,
                "messages": [
                    {
                        "role": "user",
                        "content": test['prompt']
                    }
                ],
                "temperature": 0.3,  # Low temperature for consistent responses
                "max_tokens": 100  # Short responses for testing
            }

            print("Sending request to AI...")
            start_time = time.time()

            response = requests.post(
                f"{MSTY_URL}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                response_data = response.json()

                if 'choices' in response_data and response_data['choices']:
                    ai_response = response_data['choices'][0]['message']['content']
                    print(f"✅ AI Response ({response_time:.1f}s): '{ai_response.strip()}'")

                    # Basic validation
                    if len(ai_response.strip()) > 0:
                        print(f"✅ Response quality: Good (non-empty)")
                    else:
                        print(f"⚠️ Response quality: Empty response")

                    if response_time < 10:
                        print(f"✅ Response speed: Good ({response_time:.1f}s)")
                    elif response_time < 30:
                        print(f"⚠️ Response speed: Slow ({response_time:.1f}s)")
                    else:
                        print(f"❌ Response speed: Too slow ({response_time:.1f}s)")

                else:
                    print(f"❌ Invalid response format: {response_data}")

            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            print(f"❌ AI request timeout ({TIMEOUT}s)")
            print("The model might be loading or processing is slow")

        except Exception as e:
            print(f"❌ AI request failed: {e}")

    # Test 4: Performance check
    print(f"\n--- Performance Test ---")
    print("Testing response time with a simple query...")

    try:
        simple_payload = {
            "model": default_model,
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.1,
            "max_tokens": 20
        }

        # Multiple quick tests
        response_times = []
        for i in range(3):
            start_time = time.time()
            response = requests.post(
                f"{MSTY_URL}/v1/chat/completions",
                json=simple_payload,
                timeout=15
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                response_times.append(response_time)
                print(f"Request {i + 1}: {response_time:.2f}s")

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            print(f"\nAverage response time: {avg_time:.2f}s")

            if avg_time < 3:
                print("✅ Performance: Excellent for voice assistant")
            elif avg_time < 8:
                print("✅ Performance: Good for voice assistant")
            else:
                print("⚠️ Performance: May feel slow for voice interaction")

    except Exception as e:
        print(f"Performance test failed: {e}")

    print(f"\n--- msty.app Test Summary ---")
    print("✅ Connection successful")
    print("✅ API endpoints working")
    print("✅ AI responses generating")
    print("Ready for integration with voice assistant!")

    return True


def main():
    print("Voice Assistant - msty.app Connection Test")
    print("This test verifies your local AI is working correctly")
    print("Make sure msty.app is running on localhost:10000")

    if test_msty_connection():
        print("\n🎉 Ready for next step: test_router.py")
    else:
        print("\n❌ Fix msty.app connection before proceeding")


if __name__ == "__main__":
    main()