import requests
import json

# 1. The correct endpoint includes /message
BASE_URL = "http://localhost:8000/api/v1/chat/message"
LOGIN_URL = "http://localhost:8000/api/v1/auth/login"

# (You need a valid user in your DB for this to work. You can create one via the /register endpoint if needed)
TEST_EMAIL = "test@mindbridge.ai"
TEST_PASS = "TestPass123!"

def test_memory():
    print("🧪 Testing Memory + Crisis Fix...\n")
    
    # 2. Authenticate first (the chat endpoint requires a valid user)
    auth_resp = requests.post(LOGIN_URL, json={"email": TEST_EMAIL, "password": TEST_PASS})
    if auth_resp.status_code != 200:
        print(f"❌ Login failed: {auth_resp.text}")
        print("Please ensure you have created this test user, or update the credentials!")
        return
        
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. We will capture the session_id from the first response, as it must be a valid UUID
    current_session_id = None

    def chat(message):
        nonlocal current_session_id
        payload = {"message": message}
        
        if current_session_id:
            payload["session_id"] = current_session_id
            
        response = requests.post(BASE_URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
            
        data = response.json()
        
        # Save session_id for subsequent messages
        if not current_session_id:
            current_session_id = data.get("session_id")
            
        print(f"\n👤 User: {message}")
        print(f"🤖 AI: {data.get('response', 'ERROR')}")
        print(f"📊 Details: Category={data.get('predicted_category')}, Confidence={data.get('classifier_confidence')}, MemoryUsed={data.get('memory_used')}")
        print("-" * 80)

    chat("I am very worried about my upcoming exams. I feel like I'm going to fail everything.")
    chat("yes")  # Testing the false-positive guard
    chat("What should I do to feel better? I can't stop thinking about it.")
    chat("Do you think it will actually happen?") # Ambiguous follow-up requiring context (what is "it"?)
    chat("I just really need to pass, my parents are counting on me.")

    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_memory()