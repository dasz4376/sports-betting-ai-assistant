"""
Run the complete NFL Betting AI workflow:
1. Train models on historical data
2. Make predictions for upcoming games
3. Find edges vs sportsbook odds
4. Generate betting recommendations
"""

from database import SessionLocal
from services.predictor import BettingAI


def main():
    print("\n" + "="*80)
    print("NFL BETTING AI - COMPLETE WORKFLOW")
    print("="*80)
    
    db = SessionLocal()
    ai = BettingAI(db)
    
    # Step 1: Train models (or retrain with latest data)
    print("\n[STEP 1] Training ML Models...")
    print("-" * 80)
    ai.train_all_props()
    
    # Step 2: Find upcoming games
    print("\n[STEP 2] Finding Upcoming Games...")
    print("-" * 80)
    from models import Game
    upcoming_games = db.query(Game).filter(
        Game.week == 13  # Next week
    ).limit(5).all()
    
    if not upcoming_games:
        print("No upcoming games found. Try different week number.")
        db.close()
        return
    
    print(f"Found {len(upcoming_games)} upcoming games")
    
    # Step 3: Find betting edges for each game
    print("\n[STEP 3] Finding Betting Edges...")
    print("-" * 80)
    
    all_edges = []
    for game in upcoming_games:
        print(f"\nAnalyzing: {game.away_team_name} @ {game.home_team_name}")
        edges = ai.find_edges(
            game_id=game.id,
            min_edge=10.0,      # Minimum 10% edge
            min_confidence=60.0  # Minimum 60% confidence
        )
        all_edges.extend(edges)
    
    # Step 4: Display recommendations
    print("\n[STEP 4] Betting Recommendations")
    print("="*80)
    ai.print_betting_recommendations(all_edges)
    
    print("\n[COMPLETE] Analysis finished!")
    print("Models saved to: trained_models/")
    print("="*80 + "\n")
    
    db.close()


if __name__ == "__main__":
    main()

