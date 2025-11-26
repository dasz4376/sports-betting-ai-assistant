"""
ESPN API data fetcher for NFL stats, teams, players, injuries, and schedules
"""
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from config import settings


class ESPNFetcher:
    """Fetches data from ESPN NFL APIs"""
    
    def __init__(self):
        self.base_url = settings.ESPN_BASE_URL
        self.core_url = settings.ESPN_CORE_URL
        self.sport = "football"
        self.league = "nfl"
        
    async def _get(self, url: str) -> Dict:
        """Make async GET request to ESPN API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error fetching from {url}: {e}")
                return {}
    
    async def get_all_teams(self) -> List[Dict]:
        """
        Fetch all NFL teams
        Returns: List of team dictionaries with id, name, abbreviation, etc.
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/teams"
        data = await self._get(url)
        
        teams = []
        if data and "sports" in data:
            for sport in data["sports"]:
                if "leagues" in sport:
                    for league in sport["leagues"]:
                        if "teams" in league:
                            for team_wrapper in league["teams"]:
                                team = team_wrapper.get("team", {})
                                teams.append({
                                    "espn_team_id": team.get("id"),
                                    "name": team.get("displayName"),
                                    "abbreviation": team.get("abbreviation"),
                                    "location": team.get("location"),
                                    "logo_url": team.get("logos", [{}])[0].get("href") if team.get("logos") else None
                                })
        return teams
    
    async def get_team_details(self, team_id: str) -> Dict:
        """
        Fetch detailed team information including roster
        Args:
            team_id: ESPN team ID
        Returns: Dict with team details and roster
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/teams/{team_id}"
        data = await self._get(url)
        
        team_data = data.get("team", {})
        
        # Extract roster
        roster = []
        if "athletes" in team_data:
            for athlete in team_data["athletes"]:
                roster.append({
                    "espn_player_id": athlete.get("id"),
                    "name": athlete.get("displayName"),
                    "position": athlete.get("position", {}).get("abbreviation"),
                    "jersey_number": athlete.get("jersey"),
                    "headshot_url": athlete.get("headshot", {}).get("href")
                })
        
        return {
            "team": {
                "espn_team_id": team_data.get("id"),
                "name": team_data.get("displayName"),
                "abbreviation": team_data.get("abbreviation"),
                "location": team_data.get("location"),
                "conference": team_data.get("groups", {}).get("parent", {}).get("name"),
                "division": team_data.get("groups", {}).get("name"),
            },
            "roster": roster
        }
    
    async def get_team_schedule(self, team_id: str) -> List[Dict]:
        """
        Fetch team schedule/games
        Args:
            team_id: ESPN team ID
        Returns: List of games
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/teams/{team_id}/schedule"
        data = await self._get(url)
        
        games = []
        if "events" in data:
            for event in data["events"]:
                game = event.get("competitions", [{}])[0]
                games.append({
                    "espn_game_id": event.get("id"),
                    "date": event.get("date"),
                    "status": event.get("status", {}).get("type", {}).get("name"),
                    "competitors": game.get("competitors", [])
                })
        return games
    
    async def get_scoreboard(self, season: int = None, week: int = None) -> List[Dict]:
        """
        Fetch NFL scoreboard (defaults to today's games, but can get historical)
        Args:
            season: Season year (e.g., 2024) - optional
            week: Week number (1-18) - optional
        Returns: List of games with scores and status
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/scoreboard"
        
        # Add query parameters for historical data
        params = {}
        if season and week:
            # ESPN scoreboard supports dates parameter
            # We can also use the season type and week
            params["seasontype"] = "2"  # 2 = regular season
            params["week"] = str(week)
        
        if params:
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        data = await self._get(url)
        
        games = []
        if "events" in data:
            for event in data["events"]:
                competition = event.get("competitions", [{}])[0]
                competitors = competition.get("competitors", [])
                
                home_team = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away_team = next((c for c in competitors if c.get("homeAway") == "away"), {})
                
                games.append({
                    "espn_game_id": event.get("id"),
                    "season": event.get("season", {}).get("year"),
                    "week": event.get("week", {}).get("number"),
                    "date": event.get("date"),
                    "status": event.get("status", {}).get("type", {}).get("name"),
                    "home_team_id": home_team.get("team", {}).get("id"),
                    "away_team_id": away_team.get("team", {}).get("id"),
                    "home_score": int(home_team.get("score", 0)),
                    "away_score": int(away_team.get("score", 0)),
                    "venue": competition.get("venue", {}).get("fullName")
                })
        return games
    
    async def get_game_summary(self, game_id: str) -> Dict:
        """
        Fetch detailed game summary including box score and player stats
        Args:
            game_id: ESPN game ID
        Returns: Dict with game details and player stats
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/summary?event={game_id}"
        data = await self._get(url)
        
        # Extract box score
        box_score = data.get("boxscore", {})
        players_stats = []
        
        if "players" in box_score:
            for team in box_score["players"]:
                team_id = team.get("team", {}).get("id")
                
                for stat_category in team.get("statistics", []):
                    for athlete in stat_category.get("athletes", []):
                        player_stats = {
                            "player_id": athlete.get("athlete", {}).get("id"),
                            "player_name": athlete.get("athlete", {}).get("displayName"),
                            "team_id": team_id,
                            "stats": {}
                        }
                        
                        # Parse stats
                        stats_list = athlete.get("stats", [])
                        labels = stat_category.get("labels", [])
                        
                        for label, value in zip(labels, stats_list):
                            player_stats["stats"][label.lower().replace(" ", "_")] = value
                        
                        players_stats.append(player_stats)
        
        return {
            "game_id": data.get("header", {}).get("id"),
            "players_stats": players_stats
        }
    
    async def get_player_stats(self, player_id: str) -> Dict:
        """
        Fetch player career and season statistics
        Args:
            player_id: ESPN player ID
        Returns: Dict with player stats
        """
        url = f"{self.core_url}/sports/{self.sport}/leagues/{self.league}/athletes/{player_id}/statistics"
        data = await self._get(url)
        
        return data
    
    async def get_injuries(self) -> List[Dict]:
        """
        Fetch current NFL injury report
        Returns: List of injured players with status
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/injuries"
        data = await self._get(url)
        
        injuries = []
        
        # Current API format (Nov 2025): injuries list contains teams with nested injuries
        if "injuries" in data:
            for team_data in data.get("injuries", []):
                team_id = team_data.get("id")
                
                # Each team has an "injuries" list with actual injury records
                for injury in team_data.get("injuries", []):
                    athlete = injury.get("athlete", {})
                    details = injury.get("details", {})
                    
                    # Extract player ID from links (ESPN doesn't provide it directly in injury API)
                    player_id = athlete.get("id")  # Try direct ID first
                    if not player_id:
                        # Parse from URL in links
                        links = athlete.get("links", [])
                        for link in links:
                            href = link.get("href", "")
                            if "/player/_/id/" in href:
                                # Extract ID from URL like: .../player/_/id/4428633/player-name
                                try:
                                    player_id = href.split("/player/_/id/")[1].split("/")[0]
                                    break
                                except:
                                    pass
                    
                    # Only include players who are actually injured (not Active status)
                    status = injury.get("status")
                    if status and status not in ["Active"] and player_id:
                        injuries.append({
                            "player_id": str(player_id),
                            "player_name": athlete.get("displayName"),
                            "team_id": team_id,
                            "status": status,
                            "injury_type": details.get("type", "Unknown"),
                            "description": f"{details.get('detail', '')} ({details.get('location', '')})" if details else "",
                            "date_reported": injury.get("date")
                        })
        
        # Legacy API format (pre-Nov 2025): teams > injuries
        elif "teams" in data:
            for team in data["teams"]:
                team_id = team.get("team", {}).get("id")
                
                for injury in team.get("injuries", []):
                    athlete = injury.get("athlete", {})
                    injuries.append({
                        "player_id": athlete.get("id"),
                        "player_name": athlete.get("displayName"),
                        "team_id": team_id,
                        "status": injury.get("status"),
                        "injury_type": injury.get("type"),
                        "description": injury.get("details", {}).get("type"),
                        "date_reported": injury.get("date")
                    })
        
        return injuries
    
    async def get_team_depth_chart(self, team_id: str) -> Dict:
        """
        Fetch team depth chart
        Args:
            team_id: ESPN team ID
        Returns: Dict with depth chart by position
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/teams/{team_id}/depthchart"
        data = await self._get(url)
        
        return data
    
    async def get_team_roster(self, team_id: str) -> List[Dict]:
        """
        Fetch team roster with accurate position data
        Args:
            team_id: ESPN team ID
        Returns: List of players with positions
        """
        url = f"{self.base_url}/sports/{self.sport}/{self.league}/teams/{team_id}/roster"
        data = await self._get(url)
        
        roster = []
        # Athletes are grouped by offense/defense/special teams
        for group in data.get("athletes", []):
            for athlete in group.get("items", []):
                position_data = athlete.get("position", {})
                roster.append({
                    "espn_player_id": athlete.get("id"),
                    "name": athlete.get("displayName"),
                    "position": position_data.get("abbreviation") if isinstance(position_data, dict) else position_data,
                    "jersey_number": athlete.get("jersey"),
                    "height": athlete.get("displayHeight"),
                    "weight": athlete.get("displayWeight"),
                    "age": athlete.get("age"),
                    "headshot_url": athlete.get("headshot", {}).get("href")
                })
        
        return roster


# Example usage
async def test_espn_fetcher():
    """Test the ESPN fetcher"""
    fetcher = ESPNFetcher()
    
    # Test getting all teams
    print("Fetching all NFL teams...")
    teams = await fetcher.get_all_teams()
    print(f"Found {len(teams)} teams")
    
    if teams:
        # Test getting team details
        first_team_id = teams[0]["espn_team_id"]
        print(f"\nFetching details for team {first_team_id}...")
        team_details = await fetcher.get_team_details(first_team_id)
        print(f"Roster size: {len(team_details['roster'])} players")
    
    # Test getting injuries
    print("\nFetching injury report...")
    injuries = await fetcher.get_injuries()
    print(f"Found {len(injuries)} injured players")
    
    # Test getting scoreboard
    print("\nFetching scoreboard...")
    games = await fetcher.get_scoreboard()
    print(f"Found {len(games)} games today")


if __name__ == "__main__":
    asyncio.run(test_espn_fetcher())

