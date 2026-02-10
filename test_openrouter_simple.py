"""Simple OpenRouter test without complex imports"""
from openai import OpenAI

# Test OpenRouter connection
print("=" * 60)
print("TESTING OPENROUTER CONNECTION")
print("=" * 60)

api_key = "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"
base_url = "https://openrouter.ai/api/v1"
model = "openai/gpt-4o-mini"

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    print(f"\n[OK] Client initialized successfully")
    print(f"[OK] Base URL: {base_url}")
    print(f"[OK] Model: {model}")
    
    # Test a simple completion
    print("\nTesting AI completion...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Return a JSON with a test score from 1-100. Format: {\"score\": <number>, \"message\": \"test\"}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    print(f"\n[SUCCESS] OpenRouter is working!")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"\n[ERROR] {str(e)}")

print("\n" + "=" * 60)
