"""Test script to verify AI is using real data"""
from database import SessionLocal
from services.nfl_engine import NFLEngine
from models import Player, PlayerStats, Odds

db = SessionLocal()
engine = NFLEngine(db)

print("="*60)
print("FULL PARLAY DEBUG - What data flows through?")
print("="*60)

# Simulate what happens during parlay build
print("\n1. Getting Thanksgiving games...")
games = engine.get_games_on_date("thanksgiving")
print(f"   Found {games.get('games_count')} games")

print("\n2. Building parlay for Thanksgiving...")
parlay = engine._build_parlay_data("10 leg parlay for thanksgiving")

print("\n3. Checking parlay picks for Mahomes:")
for pick in parlay.get("predictions", []):
    if "Mahomes" in pick.get("player_name", ""):
        print(f"   Player: {pick.get('player_name')}")
        print(f"   Stat: {pick.get('stat_type')}")
        print(f"   Predicted Value: {pick.get('predicted_value')}")
        print(f"   Line shown: {pick.get('line')}")
        print(f"   Book Line: {pick.get('book_line')}")
        print(f"   Using Book Line: {pick.get('using_book_line')}")
        print(f"   Betting Odds: {pick.get('betting_odds')}")
        print(f"   Odds Data: {pick.get('odds_data')}")
        break

print("\n4. Checking ALL picks for book_line vs line:")
for pick in parlay.get("predictions", []):
    player = pick.get("player_name", "Unknown")
    stat = pick.get("stat_type", "")
    line = pick.get("line", 0)
    book_line = pick.get("book_line")
    using_book = pick.get("using_book_line", False)
    odds = pick.get("betting_odds")
    print(f"   {player}: line={line}, book_line={book_line}, using_book={using_book}, odds={odds}")

db.close()
print("\nDone!")

