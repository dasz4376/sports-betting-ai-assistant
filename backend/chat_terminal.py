"""
Terminal chat interface for NFL Betting AI
Type your questions naturally!
"""

from database import SessionLocal
from services.chat_ai_v3 import ChatAI

def main():
    print("\n" + "="*80)
    print("NFL BETTING AI - CONVERSATIONAL ASSISTANT v3")
    print("="*80)
    print("\nAll predictions come from YOUR trained ML models!")
    print("Gemini just makes it conversational.\n")
    print("Ask me anything about NFL players and their stats!")
    print("Examples:")
    print("  - 'How many rushing TDs does Jalen Hurts have?'")
    print("  - 'Will Patrick Mahomes throw for 300 yards?'")
    print("  - 'What are AJ Brown's chances of scoring a TD?'")
    print("  - 'Show me Derrick Henry stats'")
    print("\nType 'quit' to exit.\n")
    print("="*80 + "\n")
    
    # Check for API key
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("GOOGLE_GEMINI_API_KEY"):
        print("\n[ERROR] GOOGLE_GEMINI_API_KEY not found in .env file!")
        print("\nTo get a FREE API key:")
        print("1. Go to: https://makersuite.google.com/app/apikey")
        print("2. Click 'Create API Key'")
        print("3. Add to your .env file: GOOGLE_GEMINI_API_KEY=your_key_here")
        print("\n(Takes 2 minutes, completely free!)\n")
        return
    
    db = SessionLocal()
    
    try:
        chat_ai = ChatAI(db)
        print("[READY] AI loaded successfully! Ask me anything...\n")
        
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nThanks for chatting! Good luck with your bets!")
                break
            
            print()  # Blank line
            response = chat_ai.chat(user_input)
            print(f"AI: {response}\n")
    
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease add your Google Gemini API key to the .env file.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

