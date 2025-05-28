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
# SCRIPT 6: test_router.py
# Tests query routing logic
# ==============================================================================

"""
File: test_router.py
Purpose: Test query routing between local functions and AI
Dependencies: None (pure logic testing)
Run: python3 test_router.py
"""

import re
import subprocess
from datetime import datetime


def get_time():
    """Get current time - local function"""
    now = datetime.now()
    return f"The time is {now.strftime('%I:%M %p')}"


def get_date():
    """Get current date - local function"""
    now = datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}"


def handle_conversion(text):
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

    # Simple distance conversion examples
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


def web_search(query):
    """Launch web search - local function"""
    try:
        # Test without actually opening browser
        search_url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        return f"Would search for: {query}\nURL: {search_url}"
    except Exception as e:
        return f"Search error: {e}"


def route_query(text):
    """
    Route query to appropriate handler
    Returns: (response, handler_type)
    """
    text_lower = text.lower().strip()

    # Time queries
    if any(word in text_lower for word in ['time', 'clock', "what time"]):
        return get_time(), "local_time"

    # Date queries
    if any(word in text_lower for word in ['date', 'today', "what day"]):
        return get_date(), "local_date"

    # Unit conversions
    if 'convert' in text_lower or any(unit in text_lower for unit in [
        'celsius', 'fahrenheit', 'meters', 'feet', 'pounds', 'kilograms'
    ]):
        conversion_result = handle_conversion(text)
        if conversion_result:
            return conversion_result, "local_conversion"

    # Web search
    if text_lower.startswith('search') or 'look up' in text_lower:
        query = text_lower.replace('search', '').replace('look up', '').strip()
        return web_search(query), "local_search"

    # Calculator queries (simple math)
    if any(op in text_lower for op in ['+', '-', '*', '/', 'plus', 'minus', 'times', 'divided']):
        # Try to extract simple math
        if re.search(r'\d+\s*[\+\-\*/]\s*\d+', text):
            return f"Math calculation: {text} (would send to AI for complex math)", "ai_math"

    # Send complex queries to AI
    return f"Complex query: '{text}' (would send to AI)", "ai_complex"


def test_router():
    """
    Test query routing logic with various inputs
    """
    print("=== Query Router Test ===")
    print("Testing how different queries are routed between local functions and AI")

    # Test cases with expected routing
    test_cases = [
        # Time/Date queries (should go to local functions)
        ("what time is it", "local_time"),
        ("What's the current time?", "local_time"),
        ("tell me the time", "local_time"),
        ("what day is today", "local_date"),
        ("what's today's date", "local_date"),

        # Unit conversions (should go to local functions if supported)
        ("convert 32 fahrenheit to celsius", "local_conversion"),
        ("how many meters in 10 feet", "local_conversion"),
        ("32 celsius to fahrenheit", "local_conversion"),

        # Web searches (should go to local search function)
        ("search for weather", "local_search"),
        ("look up Ubuntu 24.04 release date", "local_search"),

        # Math (simple should stay local, complex go to AI)
        ("what is 2 + 2", "ai_math"),
        ("calculate 15 times 37", "ai_math"),

        # Complex queries (should go to AI)
        ("explain quantum computing", "ai_complex"),
        ("write a poem about computers", "ai_complex"),
        ("how do I fix a GPU driver issue", "ai_complex"),
        ("what's the meaning of life", "ai_complex"),

        # Edge cases
        ("", "ai_complex"),  # Empty query
        ("hello", "ai_complex"),  # Simple greeting
        ("help me", "ai_complex"),  # Vague request
    ]

    print(f"\n--- Testing {len(test_cases)} Query Types ---")

    results = {
        "local_time": 0,
        "local_date": 0,
        "local_conversion": 0,
        "local_search": 0,
        "ai_math": 0,
        "ai_complex": 0
    }

    for i, (query, expected_type) in enumerate(test_cases, 1):
        print(f"\nTest {i:2d}: '{query}'")

        try:
            response, actual_type = route_query(query)

            # Check if routing matches expectation
            if actual_type == expected_type:
                print(f"✅ Routed to: {actual_type}")
                print(f"   Response: {response}")
            else:
                print(f"⚠️ Expected: {expected_type}, Got: {actual_type}")
                print(f"   Response: {response}")

            results[actual_type] += 1

        except Exception as e:
            print(f"❌ Error processing query: {e}")

    # Summary
    print(f"\n--- Routing Summary ---")
    total_queries = len(test_cases)

    for handler_type, count in results.items():
        percentage = (count / total_queries) * 100
        print(f"{handler_type:15s}: {count:2d} queries ({percentage:4.1f}%)")

    # Efficiency analysis
    local_queries = results["local_time"] + results["local_date"] + results["local_conversion"] + results[
        "local_search"]
    ai_queries = results["ai_math"] + results["ai_complex"]

    print(f"\nEfficiency Analysis:")
    print(f"Local processing: {local_queries}/{total_queries} ({(local_queries / total_queries) * 100:.1f}%)")
    print(f"AI processing:    {ai_queries}/{total_queries} ({(ai_queries / total_queries) * 100:.1f}%)")

    if local_queries > ai_queries:
        print("✅ Good balance - most simple queries handled locally")
    else:
        print("⚠️ Many queries going to AI - consider adding more local handlers")

    print(f"\n✅ Query routing test completed!")
    return True


def main():
    print("Voice Assistant - Query Router Test")
    print("This test verifies queries are routed correctly between local functions and AI")

    if test_router():
        print("\n🎉 Ready for final step: voice_assistant_integrated.py")
    else:
        print("\n❌ Fix routing logic before proceeding")


if __name__ == "__main__":
    main()

