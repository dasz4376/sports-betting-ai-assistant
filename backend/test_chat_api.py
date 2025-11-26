"""Quick test of the chat API endpoint"""
import requests
import json

def test_chat():
    url = "http://localhost:8000/api/chat"
    
    test_messages = [
        "Hello",
        "Who does Saquon Barkley play for?",
        "How will AJ Brown do next game?"
    ]
    
    print("Testing Chat API Endpoint...")
    print("="*60)
    
    for msg in test_messages:
        print(f"\nUser: {msg}")
        
        try:
            response = requests.post(
                url,
                json={"message": msg},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"AI: {data['response'][:200]}..." if len(data['response']) > 200 else f"AI: {data['response']}")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        
        except requests.exceptions.ConnectionError:
            print("ERROR: Cannot connect to backend. Make sure it's running on http://localhost:8000")
            break
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "="*60)
    print("Test complete!")

if __name__ == "__main__":
    test_chat()


