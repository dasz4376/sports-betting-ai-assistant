"""
The Odds API fetcher for NFL odds and player props
"""
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from config import settings


class OddsFetcher:
    """Fetches odds data from The Odds API"""
    
    def __init__(self):
        self.base_url = settings.ODDS_API_BASE_URL
        self.api_key = settings.ODDS_API_KEY
        self.region = settings.ODDS_API_REGION
        self.sport_key = "americanfootball_nfl"
        
    async def _get(self, url: str, params: Dict = None) -> Dict:
        """Make async GET request to The Odds API"""
        if params is None:
            params = {}
        
        # Add API key to all requests
        params["apiKey"] = self.api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Check remaining API quota
                remaining = response.headers.get("x-requests-remaining")
                used = response.headers.get("x-requests-used")
                if remaining:
                    print(f"API Quota - Used: {used}, Remaining: {remaining}")
                
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching from {url}: {e}")
                return {}
    
    async def get_nfl_odds(self, markets: str = None) -> List[Dict]:
        """
        Fetch NFL game odds (moneyline, spreads, totals)
        Args:
            markets: Comma-separated markets (h2h, spreads, totals)
        Returns: List of games with odds from multiple bookmakers
        """
        if markets is None:
            markets = settings.ODDS_API_MARKETS
        
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "regions": self.region,
            "markets": markets,
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        
        data = await self._get(url, params)
        
        games_with_odds = []
        if isinstance(data, list):
            for game in data:
                game_odds = {
                    "odds_api_id": game.get("id"),
                    "commence_time": game.get("commence_time"),
                    "home_team": game.get("home_team"),
                    "away_team": game.get("away_team"),
                    "bookmakers": []
                }
                
                # Parse odds from each bookmaker
                for bookmaker in game.get("bookmakers", []):
                    bookmaker_data = {
                        "name": bookmaker.get("key"),
                        "title": bookmaker.get("title"),
                        "markets": {}
                    }
                    
                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key")
                        outcomes = market.get("outcomes", [])
                        
                        if market_key == "h2h":  # Moneyline
                            bookmaker_data["markets"]["moneyline"] = {
                                outcome.get("name"): outcome.get("price")
                                for outcome in outcomes
                            }
                        
                        elif market_key == "spreads":  # Spread
                            bookmaker_data["markets"]["spreads"] = {
                                outcome.get("name"): {
                                    "point": outcome.get("point"),
                                    "price": outcome.get("price")
                                }
                                for outcome in outcomes
                            }
                        
                        elif market_key == "totals":  # Over/Under
                            bookmaker_data["markets"]["totals"] = {
                                outcome.get("name"): {
                                    "point": outcome.get("point"),
                                    "price": outcome.get("price")
                                }
                                for outcome in outcomes
                            }
                    
                    game_odds["bookmakers"].append(bookmaker_data)
                
                games_with_odds.append(game_odds)
        
        return games_with_odds
    
    async def get_nfl_player_props(self) -> List[Dict]:
        """
        Fetch ALL 46 NFL player prop markets from The Odds API
        
        Markets include:
        - Passing: yards, TDs, completions, attempts, INTs, longest completion (+ alternates, quarters/halves)
        - Rushing: yards, attempts, longest rush (+ alternates, quarters/halves)
        - Receiving: yards, receptions, longest reception (+ alternates, quarters/halves)
        - Combined: pass+rush, rush+rec, pass+rush+rec yards
        - Touchdowns: 1st TD, anytime TD, last TD, TD over (+ quarters/halves)
        - Kicking: field goals, kicking points, PATs
        
        Returns: List of player props with odds from multiple bookmakers
        """
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "regions": self.region,
            "markets": settings.ODDS_API_PROP_MARKETS,
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        
        data = await self._get(url, params)
        
        props_list = []
        if isinstance(data, list):
            for game in data:
                game_info = {
                    "odds_api_id": game.get("id"),
                    "commence_time": game.get("commence_time"),
                    "home_team": game.get("home_team"),
                    "away_team": game.get("away_team")
                }
                
                # Parse player props from each bookmaker
                for bookmaker in game.get("bookmakers", []):
                    bookmaker_name = bookmaker.get("key")
                    
                    for market in bookmaker.get("markets", []):
                        market_type = market.get("key")
                        
                        for outcome in market.get("outcomes", []):
                            prop = {
                                **game_info,
                                "bookmaker": bookmaker_name,
                                "prop_type": market_type,
                                "player_name": outcome.get("description"),
                                "line": outcome.get("point"),
                                "over_under": outcome.get("name"),  # "Over" or "Under"
                                "odds": outcome.get("price"),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            props_list.append(prop)
        
        return props_list
    
    async def get_available_sports(self) -> List[Dict]:
        """
        Fetch list of all available sports
        Returns: List of sports with their keys
        """
        url = f"{self.base_url}/sports"
        data = await self._get(url)
        
        return data if isinstance(data, list) else []
    
    def convert_american_to_decimal(self, american_odds: int) -> float:
        """
        Convert American odds to decimal odds
        Args:
            american_odds: American odds (e.g., -110, +150)
        Returns: Decimal odds
        """
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def calculate_implied_probability(self, american_odds: int) -> float:
        """
        Calculate implied probability from American odds
        Args:
            american_odds: American odds (e.g., -110, +150)
        Returns: Implied probability as a percentage
        """
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def calculate_parlay_odds(self, odds_list: List[int]) -> Dict:
        """
        Calculate combined parlay odds from multiple legs
        Args:
            odds_list: List of American odds for each leg
        Returns: Dict with combined decimal odds, American odds, and payout multiplier
        """
        # Convert all to decimal odds
        decimal_odds = [self.convert_american_to_decimal(odds) for odds in odds_list]
        
        # Multiply all decimal odds together
        combined_decimal = 1.0
        for odds in decimal_odds:
            combined_decimal *= odds
        
        # Convert back to American odds
        if combined_decimal >= 2.0:
            combined_american = (combined_decimal - 1) * 100
        else:
            combined_american = -100 / (combined_decimal - 1)
        
        return {
            "decimal_odds": round(combined_decimal, 2),
            "american_odds": round(combined_american),
            "payout_multiplier": round(combined_decimal, 2)
        }
    
    def find_best_odds(self, bookmakers_data: List[Dict], market_type: str) -> Dict:
        """
        Find the best odds across all bookmakers for a specific market
        Args:
            bookmakers_data: List of bookmaker data from get_nfl_odds
            market_type: "moneyline", "spreads", or "totals"
        Returns: Dict with best odds for each outcome
        """
        best_odds = {}
        
        for bookmaker in bookmakers_data:
            if market_type in bookmaker.get("markets", {}):
                market_data = bookmaker["markets"][market_type]
                
                for outcome, value in market_data.items():
                    if isinstance(value, dict):
                        odds = value.get("price")
                    else:
                        odds = value
                    
                    if outcome not in best_odds or abs(odds) < abs(best_odds[outcome]["odds"]):
                        best_odds[outcome] = {
                            "odds": odds,
                            "bookmaker": bookmaker["name"]
                        }
        
        return best_odds


# Example usage
async def test_odds_fetcher():
    """Test the Odds API fetcher"""
    fetcher = OddsFetcher()
    
    # Check if API key is set
    if not fetcher.api_key:
        print("WARNING: ODDS_API_KEY not set in configuration!")
        print("Get your free API key at: https://the-odds-api.com/")
        return
    
    # Test getting available sports
    print("Fetching available sports...")
    sports = await fetcher.get_available_sports()
    nfl_sport = next((s for s in sports if "nfl" in s.get("key", "").lower()), None)
    if nfl_sport:
        print(f"NFL found: {nfl_sport}")
    
    # Test getting NFL game odds
    print("\nFetching NFL game odds...")
    game_odds = await fetcher.get_nfl_odds()
    print(f"Found odds for {len(game_odds)} games")
    
    if game_odds:
        first_game = game_odds[0]
        print(f"\nExample game: {first_game['away_team']} @ {first_game['home_team']}")
        print(f"Number of bookmakers: {len(first_game['bookmakers'])}")
        
        # Find best moneyline odds
        best_ml = fetcher.find_best_odds(first_game["bookmakers"], "moneyline")
        print(f"Best moneyline odds: {best_ml}")
    
    # Test getting player props
    print("\nFetching NFL player props...")
    props = await fetcher.get_nfl_player_props()
    print(f"Found {len(props)} player props")
    
    if props:
        # Show example prop
        example_prop = props[0]
        print(f"\nExample prop: {example_prop['player_name']} - {example_prop['prop_type']}")
        print(f"Line: {example_prop['line']} | {example_prop['over_under']}: {example_prop['odds']}")
        
        # Calculate implied probability
        implied_prob = fetcher.calculate_implied_probability(example_prop['odds'])
        print(f"Implied probability: {implied_prob * 100:.1f}%")
    
    # Test parlay calculator
    print("\n--- Parlay Calculator Test ---")
    sample_odds = [-110, -110, +150]
    parlay_result = fetcher.calculate_parlay_odds(sample_odds)
    print(f"3-leg parlay ({sample_odds}):")
    print(f"Combined odds: {parlay_result['american_odds']:+d}")
    print(f"$10 bet would pay: ${10 * parlay_result['payout_multiplier']:.2f}")


if __name__ == "__main__":
    asyncio.run(test_odds_fetcher())

