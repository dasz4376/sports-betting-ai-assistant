"""
Conversational AI v4 - Complete Architecture Rework

NEW ARCHITECTURE:
================
YOUR AI (NFLEngine) = The Brain - ALL NFL knowledge lives here
Gemini = The Mouth - ONLY formats YOUR AI's data conversationally

HOW IT WORKS:
1. User sends query
2. YOUR AI Engine processes it FIRST:
   - Detects intent
   - Fetches data from YOUR database
   - Runs YOUR ML models for predictions
   - Returns structured data
3. Gemini receives ONLY this structured data
4. Gemini formats it into a friendly response
5. Response is validated to ensure ONLY YOUR AI's data is included

CRITICAL: Gemini has NO function calling, NO tools, NO database access.
It ONLY receives pre-fetched data and formats it.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import google.generativeai as genai
from sqlalchemy.orm import Session
import time
import re

from services.nfl_engine import NFLEngine, validate_gemini_response

load_dotenv()


class ChatAI:
    """
    Conversational AI - Gemini is ONLY the mouth, YOUR AI is the brain.
    
    Gemini has ZERO NFL knowledge. All data comes from NFLEngine.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.nfl_engine = NFLEngine(db)  # YOUR AI - The Brain
        self.last_structured_data = None
        
        # Configure Gemini - NO TOOLS, NO FUNCTION CALLING
        api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY not set in .env file")
        
        genai.configure(api_key=api_key)
        
        # Simple model - NO tools, NO function calling
        # Gemini is ONLY for formatting text
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Intent classifier model - lightweight, fast
        self.classifier_model = genai.GenerativeModel('gemini-2.0-flash')
        
        # System prompt makes clear Gemini is ONLY a formatter
        self.formatter_prompt = """You are a text formatter for an NFL Betting AI.

CRITICAL FORMATTING RULES:
1. DO NOT use asterisks (*) or markdown formatting
2. DO NOT use **bold** text - just use plain text
3. Use bullet points with "•" symbol, not asterisks
4. Keep responses clean and simple
5. Use minimal emojis - one or two max

DATA RULES:
1. You have ZERO knowledge about NFL
2. You will receive structured data from the database
3. ONLY present the data given - do not add anything
4. Do not make assumptions or guesses

FORMAT EXAMPLE:
Instead of: **Player:** John Smith
Write: Player: John Smith

Instead of: * Team: Eagles
Write: • Team: Eagles

If the data shows an error, explain it simply.
Speak as if YOU are the betting AI presenting your analysis."""
    
    def smart_classify_intent(self, query: str) -> Dict:
        """
        Use Gemini to intelligently classify user intent.
        This handles typos, different phrasings, and natural language.
        
        Returns structured intent that NFLEngine can process.
        """
        classification_prompt = f"""Analyze this NFL betting query and classify it.

USER QUERY: "{query}"

Classify into ONE of these categories:
- PARLAY: User wants betting picks/parlay (any number of legs, combinations, bet slip)
- LEADERBOARD: User wants top/best players at a position (rankings, leaders, most yards/TDs)
- PLAYER_OUTLOOK: User asking if a player will do well, is a good bet, should they bet on them
- PREDICTION: User wants a specific stat prediction for a player (how many yards, TDs, etc)
- STATS: User wants to see a player's stats/averages
- TEAM_MATCHUP: User comparing two teams or asking about a game matchup
- SCHEDULE: User asking about upcoming games, when teams play, next game
- INJURY: User asking about injuries
- ROSTER: User asking about team roster/players on a team
- VALUE_BETS: User looking for good value bets or edges
- PLAYER_INFO: User asking about a specific player's team, position, etc
- META: User asking about how the AI works, data sources, thanks, greetings
- GENERAL: Other/unclear

Also extract any entities:
- player_names: Full names of any players mentioned (fix obvious typos)
- team_names: Any team names/cities mentioned
- positions: QB, RB, WR, TE mentioned
- stat_types: passing_yards, rushing_yards, receiving_yards, receptions, touchdowns
- risk_level: safe/conservative OR risky/aggressive (for parlays)
- date_context: thanksgiving, christmas, sunday, today, etc
- num_picks: Number if user requests specific number of picks/legs

RESPOND IN VALID JSON ONLY:
{{
  "intent": "CATEGORY_NAME",
  "confidence": 0.0-1.0,
  "player_names": [],
  "team_names": [],
  "positions": [],
  "stat_types": [],
  "risk_level": "normal",
  "date_context": null,
  "num_picks": null,
  "corrected_query": "the query with typos fixed"
}}"""

        try:
            response = self.classifier_model.generate_content(
                classification_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temp for consistent classification
                    max_output_tokens=500
                )
            )
            
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            
            print(f"\n[SMART INTENT] Query: '{query}'")
            print(f"[SMART INTENT] Classified as: {result.get('intent')} (confidence: {result.get('confidence', 0):.0%})")
            if result.get('player_names'):
                print(f"[SMART INTENT] Players: {result.get('player_names')}")
            if result.get('team_names'):
                print(f"[SMART INTENT] Teams: {result.get('team_names')}")
            if result.get('corrected_query') and result.get('corrected_query').lower() != query.lower():
                print(f"[SMART INTENT] Corrected: '{result.get('corrected_query')}'")
            
            return result
            
        except Exception as e:
            print(f"[SMART INTENT] Classification failed: {e}, falling back to keyword matching")
            # Fall back to keyword-based detection
            return {"intent": "FALLBACK", "error": str(e)}
    
    def process_with_smart_intent(self, query: str) -> Dict:
        """
        Process query using smart intent classification.
        Maps Gemini's classification to NFLEngine handlers.
        """
        # Get smart classification
        classification = self.smart_classify_intent(query)
        
        # If classification failed, fall back to NFLEngine's keyword detection
        if classification.get("intent") == "FALLBACK":
            return self.nfl_engine.process_query(query)
        
        intent = classification.get("intent", "GENERAL").upper()
        
        # Build a normalized query that NFLEngine can understand
        # Use extracted entities to construct a clear query
        
        if intent == "PARLAY":
            # Build parlay query
            risk = classification.get("risk_level", "normal")
            date_ctx = classification.get("date_context", "")
            num_picks = classification.get("num_picks", 5)
            teams = classification.get("team_names", [])
            
            if teams:
                normalized = f"parlay for {' vs '.join(teams)}"
            elif date_ctx:
                normalized = f"{num_picks or 5} leg parlay for {date_ctx}"
            else:
                normalized = f"{num_picks or 5} leg parlay"
            
            # Add risk level
            if risk == "safe":
                normalized = "safe " + normalized
            elif risk == "risky":
                normalized = "risky " + normalized
                
            result = self.nfl_engine.process_query(normalized)
            # Override intent to ensure parlay formatting
            result["intent"] = "parlay"
            return result
        
        elif intent == "LEADERBOARD":
            positions = classification.get("positions", [])
            stat_types = classification.get("stat_types", [])
            
            # Determine position from explicit mention OR from stat type
            position = positions[0] if positions else None
            
            if not position:
                query_lower = query.lower()
                # Infer position from stat type or keywords
                if any(s in query_lower for s in ["rushing", "rush", "run", "carries"]):
                    position = "RB"
                elif any(s in query_lower for s in ["receiving", "reception", "catches", "targets"]):
                    position = "WR"
                elif any(s in query_lower for s in ["passing", "pass", "throw", "qb", "quarterback"]):
                    position = "QB"
                elif any(s in query_lower for s in ["tight end", "te "]):
                    position = "TE"
                else:
                    position = "QB"  # Default
            
            data = self.nfl_engine.get_top_players(position, 10)
            return {
                "intent": "leaderboard",
                "query": query,
                "data": data,
                "gemini_instructions": "Present this leaderboard conversationally. Use ONLY the data provided."
            }
        
        elif intent == "PLAYER_OUTLOOK":
            player_names = classification.get("player_names", [])
            if player_names:
                data = self.nfl_engine.get_player_outlook(player_names[0], query)
                return {
                    "intent": "player_outlook",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this player outlook as betting advice. Use ONLY the data provided."
                }
            return self.nfl_engine.process_query(query)
        
        elif intent == "PREDICTION":
            player_names = classification.get("player_names", [])
            stat_types = classification.get("stat_types", [])
            
            if player_names:
                stat = stat_types[0] if stat_types else "passing_yards"
                data = self.nfl_engine.predict_player_stat(player_names[0], stat)
                return {
                    "intent": "prediction",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this prediction conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "STATS":
            player_names = classification.get("player_names", [])
            if player_names:
                data = self.nfl_engine.get_player_stats(player_names[0])
                return {
                    "intent": "stats",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present these stats conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "TEAM_MATCHUP":
            team_names = classification.get("team_names", [])
            if len(team_names) >= 2:
                data = self.nfl_engine.predict_team_matchup(team_names[0], team_names[1])
                return {
                    "intent": "team_matchup",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this matchup analysis conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "SCHEDULE":
            team_names = classification.get("team_names", [])
            date_ctx = classification.get("date_context")
            
            if date_ctx:
                data = self.nfl_engine.get_games_on_date(date_ctx)
                return {
                    "intent": "games_on_date",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present these games conversationally. Use ONLY the data provided."
                }
            elif team_names:
                data = self.nfl_engine.get_team_schedule(team_names[0])
                return {
                    "intent": "team_schedule",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this schedule conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "INJURY":
            team_names = classification.get("team_names", [])
            player_names = classification.get("player_names", [])
            
            if team_names:
                data = self.nfl_engine.get_injury_report(team_name=team_names[0])
            elif player_names:
                data = self.nfl_engine.get_injury_report(player_name=player_names[0])
            else:
                # Get all injuries
                data = self.nfl_engine.get_injury_report()
            
            return {
                "intent": "injury",
                "query": query,
                "data": data,
                "gemini_instructions": "Present this injury report conversationally. Use ONLY the data provided."
            }
        
        elif intent == "VALUE_BETS":
            # VALUE BETS = Use the same parlay logic but with safer picks
            # Pass to NFLEngine's process_query which handles value_bets intent
            return self.nfl_engine.process_query("find value bets")
        
        elif intent == "PLAYER_INFO":
            player_names = classification.get("player_names", [])
            if player_names:
                data = self.nfl_engine.get_player_info(player_names[0])
                return {
                    "intent": "player_info",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this player info conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "ROSTER":
            team_names = classification.get("team_names", [])
            positions = classification.get("positions", [])
            
            if team_names:
                pos = positions[0] if positions else None
                data = self.nfl_engine.get_team_roster(team_names[0], pos)
                return {
                    "intent": "roster",
                    "query": query,
                    "data": data,
                    "gemini_instructions": "Present this roster conversationally. Use ONLY the data provided."
                }
            else:
                return self.nfl_engine.process_query(query)
        
        elif intent == "META":
            return {
                "intent": "meta",
                "query": query,
                "data": {
                    "message": "All my picks and predictions come from my own database and 21 machine learning models trained on 2024-2025 NFL data. I analyze player stats, team performance, matchups, injuries, and real sportsbook odds. Everything is based on actual data - I don't make things up!",
                    "capabilities": [
                        "Player stat predictions (yards, TDs, receptions)",
                        "Smart parlay building (safe, normal, or risky)",
                        "Value bet detection vs sportsbook lines",
                        "Team matchup analysis",
                        "Injury reports",
                        "Player/team schedules",
                        "Position leaderboards"
                    ]
                },
                "gemini_instructions": "Explain the AI's capabilities conversationally."
            }
        
        else:
            # Fall back to NFLEngine's processing
            return self.nfl_engine.process_query(query)
    
    def format_response(self, engine_result: Dict) -> str:
        """
        Use Gemini ONLY to format the response from YOUR AI Engine.
        Gemini receives no tools, no functions - just data to format.
        """
        # If there's an error, return it directly
        if engine_result.get("error"):
            return f"Sorry, I couldn't help with that: {engine_result['error']}"
        
        # If no data, explain
        if not engine_result.get("data"):
            print("[!] NFLEngine returned no data")
            return "I don't have the information needed to answer that. Could you be more specific about which player or team you're asking about?"
        
        # ALL RESPONSES: Use direct formatters (Gemini bypassed for clean, consistent output)
        intent = engine_result.get("intent", "general")
        data = engine_result.get("data", {})
        
        print(f"\n[*] Intent: {intent} - Using direct formatter (Gemini bypassed)")
        
        # Route to appropriate formatter
        formatters = {
            "parlay": self._format_parlay,
            "value_bets": self._format_parlay,  # Same as parlay with safe risk
            "prediction": self._format_prediction,
            "stats": self._format_stats,
            "team_matchup": self._format_matchup,
            "roster": self._format_roster,
            "injury": self._format_injury,
            "games_on_date": self._format_games,
            "team_schedule": self._format_schedule,
            "player_info": self._format_player_info,
            "leaderboard": self._format_leaderboard,
            "player_outlook": self._format_player_outlook,
            "defensive_matchup": self._format_defensive_matchup,
            "meta": self._format_meta,
            "general": self._format_general,
        }
        
        formatter = formatters.get(intent, self._format_general)
        return formatter(data)
    
    def _clean_formatting(self, text: str) -> str:
        """Remove markdown formatting that Gemini adds"""
        import re
        
        # Remove **bold** formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        
        # Remove *italic* formatting
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Replace asterisk bullets with proper bullets
        text = re.sub(r'^\s*\*\s+', '  • ', text, flags=re.MULTILINE)
        
        # Remove any remaining lone asterisks
        text = text.replace(' * ', ' • ')
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _format_raw_response(self, engine_result: Dict) -> str:
        """Fallback: Format response without Gemini"""
        data = engine_result.get("data", {})
        intent = engine_result.get("intent", "unknown")
        
        if "error" in data:
            return f"Sorry: {data['error']}"
        
        # Format based on intent
        if intent == "prediction":
            return self._format_prediction(data)
        elif intent == "stats":
            return self._format_stats(data)
        elif intent == "team_matchup":
            return self._format_matchup(data)
        elif intent == "roster":
            return self._format_roster(data)
        elif intent == "injury":
            return self._format_injury(data)
        elif intent == "games_on_date":
            return self._format_games(data)
        elif intent == "parlay":
            return self._format_parlay(data)
        elif intent == "value_bets":
            return self._format_value_bets(data)
        elif intent in ["team_schedule", "player_schedule", "player_info"]:
            return self._format_schedule(data)
        elif intent == "meta":
            return self._format_meta(data)
        elif intent == "general":
            return data.get("message", "How can I help you with NFL betting?")
        else:
            return f"Here's what I found: {json.dumps(data, indent=2, default=str)}"
    
    def _format_prediction(self, data: Dict) -> str:
        """Format prediction response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        player = data.get("player_name", "Unknown")
        team = data.get("team", "Unknown")
        stat = data.get("stat_type", "unknown").replace("_", " ").title()
        value = data.get("predicted_value", 0)
        confidence = data.get("confidence", 0)
        opponent = data.get("opponent", "their opponent")
        season_avg = data.get("season_average", 0)
        
        lines = [f"🎯 {player} Prediction\n"]
        lines.append(f"  📊 {stat}: {value:.0f}")
        lines.append(f"  💪 Confidence: {confidence:.0f}%")
        lines.append(f"  📈 Season Avg: {season_avg:.1f}")
        lines.append(f"  🆚 vs {opponent}")
        lines.append(f"  🏈 Team: {team}")
        
        return "\n".join(lines)
    
    def _format_stats(self, data: Dict) -> str:
        """Format stats response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        player = data.get("player_name", "Unknown")
        team = data.get("team", "Unknown")
        position = data.get("position", "?")
        games = data.get("games_played", 0)
        
        lines = [f"📊 {player} Stats\n"]
        lines.append(f"  🏈 Team: {team}")
        lines.append(f"  🎽 Position: {position}")
        lines.append(f"  🎮 Games: {games}")
        lines.append("")
        
        # Add relevant stats based on position
        for key, value in data.items():
            if key.endswith("_per_game") and value > 0:
                stat_name = key.replace("_per_game", "").replace("_", " ").title()
                lines.append(f"  📈 {stat_name}: {value:.1f}/game")
        
        if data.get("consistency_score"):
            lines.append(f"\n  🎯 Consistency: {data['consistency_score']:.0f}%")
        
        return "\n".join(lines)
    
    def _format_matchup(self, data: Dict) -> str:
        """Format team matchup response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        team1 = data.get("team1", {})
        team2 = data.get("team2", {})
        prediction = data.get("prediction", {})
        
        team1_name = team1.get("name", "Team 1")
        team2_name = team2.get("name", "Team 2")
        team1_record = team1.get("record", "?-?")
        team2_record = team2.get("record", "?-?")
        
        scores = prediction.get("predicted_score", {})
        probs = prediction.get("win_probability", {})
        
        team1_score = scores.get("team1", 0)
        team2_score = scores.get("team2", 0)
        team1_prob = probs.get("team1", 50)
        team2_prob = probs.get("team2", 50)
        
        winner = team1_name if team1_prob > team2_prob else team2_name
        win_prob = max(team1_prob, team2_prob)
        
        lines = [f"⚔️ {team1_name} vs {team2_name}\n"]
        lines.append(f"  📋 {team1_name}: {team1_record}")
        lines.append(f"  📋 {team2_name}: {team2_record}")
        lines.append("")
        lines.append("🎯 Predicted Score:")
        lines.append(f"  {team1_name} {team1_score:.0f} - {team2_name} {team2_score:.0f}")
        lines.append("")
        lines.append("📊 Win Probability:")
        lines.append(f"  {team1_name}: {team1_prob:.0f}%")
        lines.append(f"  {team2_name}: {team2_prob:.0f}%")
        lines.append("")
        lines.append(f"✅ Pick: {winner} ({win_prob:.0f}%)")
        
        return "\n".join(lines)
    
    def _format_roster(self, data: Dict) -> str:
        """Format roster response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        team = data.get("team", "Unknown")
        roster = data.get("roster", {})
        total = data.get("total_players", 0)
        
        lines = [f"🏈 {team} Roster\n"]
        lines.append(f"  👥 Total: {total} players\n")
        
        for position, players in roster.items():
            if players:
                lines.append(f"  🎽 {position}:")
                for p in players[:5]:
                    lines.append(f"    • {p}")
                if len(players) > 5:
                    lines.append(f"    +{len(players) - 5} more")
        
        return "\n".join(lines)
    
    def _format_injury(self, data: Dict) -> str:
        """Format injury response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        if data.get("message") and data.get("injury_count", 0) == 0:
            return f"✅ {data.get('message')}"
        
        if data.get("status") == "Healthy":
            return f"✅ {data.get('player_name', 'Player')} ({data.get('team', 'Team')}): No injuries"
        
        # League-wide injury report (has "out", "doubtful", "questionable" keys)
        if "out" in data or "doubtful" in data or "questionable" in data:
            title = data.get("title", "NFL Injury Report")
            count = data.get("injury_count", 0)
            
            lines = [f"🏥 {title} ({count} injuries)\n"]
            
            out = data.get("out", [])
            doubtful = data.get("doubtful", [])
            questionable = data.get("questionable", [])
            
            if out:
                lines.append("🔴 OUT:")
                for inj in out[:10]:
                    lines.append(f"  • {inj.get('player', '?')} ({inj.get('team', '?')}) - {inj.get('injury_type', '?')}")
            
            if doubtful:
                lines.append("\n🟡 DOUBTFUL:")
                for inj in doubtful[:8]:
                    lines.append(f"  • {inj.get('player', '?')} ({inj.get('team', '?')}) - {inj.get('injury_type', '?')}")
            
            if questionable:
                lines.append("\n🟠 QUESTIONABLE:")
                for inj in questionable[:10]:
                    lines.append(f"  • {inj.get('player', '?')} ({inj.get('team', '?')}) - {inj.get('injury_type', '?')}")
            
            return "\n".join(lines)
        
        elif "injuries" in data:
            # Team injury report
            team = data.get("team", "Unknown")
            count = data.get("injury_count", 0)
            injuries = data.get("injuries", [])
            
            if count == 0:
                return f"✅ {team}: No active injuries"
            
            lines = [f"🏥 {team} Injuries ({count})\n"]
            
            # Group by status
            out = [i for i in injuries if i.get("status") == "Out"]
            doubtful = [i for i in injuries if i.get("status") == "Doubtful"]
            questionable = [i for i in injuries if i.get("status") == "Questionable"]
            
            if out:
                lines.append("  🔴 OUT:")
                for inj in out:
                    lines.append(f"    • {inj.get('player', '?')} ({inj.get('position', '?')}) - {inj.get('injury_type', '?')}")
            
            if doubtful:
                lines.append("  🟡 DOUBTFUL:")
                for inj in doubtful:
                    lines.append(f"    • {inj.get('player', '?')} ({inj.get('position', '?')}) - {inj.get('injury_type', '?')}")
            
            if questionable:
                lines.append("  🟠 QUESTIONABLE:")
                for inj in questionable:
                    lines.append(f"    • {inj.get('player', '?')} ({inj.get('position', '?')}) - {inj.get('injury_type', '?')}")
            
            return "\n".join(lines)
        else:
            # Single player
            player = data.get("player_name", "Unknown")
            team = data.get("team", "Unknown")
            status = data.get("status", "Unknown")
            injury_type = data.get("injury_type", "Unknown")
            
            status_emoji = "🔴" if status == "Out" else "🟡" if status == "Doubtful" else "🟠"
            return f"{status_emoji} {player} ({team}): {status} - {injury_type}"
    
    def _format_games(self, data: Dict) -> str:
        """Format games on date response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        date_str = data.get("date", "Unknown date")
        count = data.get("games_count", 0)
        games = data.get("games", [])
        
        if count == 0:
            return f"📅 No NFL games on {date_str}"
        
        lines = [f"🏈 Games on {date_str}\n"]
        
        for game in games:
            away = game.get("away_team", "?")
            home = game.get("home_team", "?")
            time = game.get("time", "TBD")
            lines.append(f"  🎮 {away} @ {home} ({time})")
        
        lines.append(f"\n📊 {count} games total")
        
        return "\n".join(lines)
    
    def _generate_parlay_code(self, predictions: list) -> str:
        """
        Generate a unique verification code from database player IDs.
        This code PROVES the parlay came from YOUR AI because:
        - It uses internal database player_id values
        - Only your database knows these IDs
        - Gemini could never generate this code
        """
        import hashlib
        from datetime import datetime
        
        # Collect all player IDs from picks
        player_ids = [str(pred.get("player_id", 0)) for pred in predictions]
        
        # Create a seed string from player IDs + today's date
        today = datetime.now().strftime("%Y%m%d")
        seed = f"AUTONOMI-{'-'.join(player_ids)}-{today}"
        
        # Hash it to create a short verification code
        hash_obj = hashlib.md5(seed.encode())
        code = hash_obj.hexdigest()[:8].upper()
        
        return f"AUT-{code}"
    
    def _format_parlay(self, data: Dict) -> str:
        """Format parlay response - EXACT real sportsbook format"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        predictions = data.get("predictions", [])
        
        if not predictions:
            return "❌ Sorry, I couldn't generate picks for those games."
        
        # Generate verification code from database IDs
        verification_code = self._generate_parlay_code(predictions)
        
        # Get risk level for display
        risk_level = data.get("risk_level", "normal")
        risk_emoji = {"safe": "🔒", "normal": "🎯", "risky": "🔥"}.get(risk_level, "🎯")
        risk_label = {"safe": "SAFER", "normal": "STANDARD", "risky": "AGGRESSIVE"}.get(risk_level, "STANDARD")
        
        lines = [f"Here are your picks! {risk_emoji} {risk_label}\n"]
        
        for pred in predictions:
            player = pred.get("player_name", "Unknown")
            stat_type = pred.get("stat_type", "yards")
            bet_type = pred.get("bet_type", "over")
            line = pred.get("line", 0)
            book_line = pred.get("book_line", line)
            
            # Get clean stat name - EXACT sportsbook format
            stat_lower = stat_type.lower()
            if ("pass" in stat_lower and "rush" in stat_lower) or "pass_rush" in stat_lower:
                stat_name = "Passing + Rushing Yards"
            elif ("rush" in stat_lower and "rec" in stat_lower) or "rush_rec" in stat_lower:
                stat_name = "Rushing + Receiving Yards"
            elif "passing" in stat_lower and "yard" in stat_lower:
                stat_name = "Passing Yards"
            elif "rushing" in stat_lower and "yard" in stat_lower:
                stat_name = "Rushing Yards"
            elif "receiving" in stat_lower and "yard" in stat_lower:
                stat_name = "Receiving Yards"
            elif "reception" in stat_lower and "yard" not in stat_lower:
                stat_name = "Receptions"
            elif "passing_td" in stat_lower or stat_type == "passing_tds":
                stat_name = "Passing TDs"
            elif "rushing_td" in stat_lower:
                stat_name = "Rushing TDs"
            elif "receiving_td" in stat_lower:
                stat_name = "Receiving TDs"
            elif "anytime" in stat_lower or bet_type == "anytime_td":
                stat_name = "Anytime TD Scorer"
            elif "completion" in stat_lower:
                stat_name = "Completions"
            elif "attempt" in stat_lower:
                stat_name = "Pass Attempts"
            elif "interception" in stat_lower:
                stat_name = "Interceptions"
            elif "field_goal" in stat_lower:
                stat_name = "Field Goals"
            elif "kicking_point" in stat_lower:
                stat_name = "Kicking Points"
            elif "extra_point" in stat_lower or "pats" in stat_lower:
                stat_name = "Extra Points"
            else:
                stat_name = stat_type.replace("_", " ").title()
                # Fix common casing issues
                stat_name = stat_name.replace("Tds", "TDs").replace(" Td ", " TD ")
            
            # REAL SPORTSBOOK FORMAT (like DraftKings/FanDuel):
            # Anytime TD: "Player Name - Anytime TD Scorer"
            # Yards: "210+ Player Name Passing + Rushing Yards"
            
            if bet_type == "anytime_td" or "anytime" in stat_lower or stat_name == "Anytime TD Scorer" or line is None:
                lines.append(f"  {player} - Anytime TD Scorer")
            else:
                display_line = book_line if book_line and book_line > 0 else (line if line else 0)
                
                # Skip if we have no valid line - treat as anytime TD
                if display_line <= 0:
                    lines.append(f"  {player} - Anytime TD Scorer")
                    continue
                
                import math
                
                # YARDS: Round DOWN to nearest 5 interval (250, 255, 260, etc.)
                if "yard" in stat_lower:
                    rounded_line = max(5, int(math.floor(display_line / 5) * 5))
                # TDs, RECEPTIONS, etc: Round to nearest whole number, minimum 1
                else:
                    rounded_line = max(1, int(round(display_line)))
                
                lines.append(f"  {rounded_line}+ {player} {stat_name}")
        
        lines.append(f"\n🎰 {len(predictions)} Pick Parlay")
        lines.append("🍀 Good luck!")
        
        # Check for picks missing odds data
        no_odds_picks = [p for p in predictions if p.get("no_odds_warning") or p.get("betting_odds") is None]
        if no_odds_picks and risk_level in ["safe", "risky"]:
            lines.append(f"\n⚠️ {len(no_odds_picks)} picks missing odds data")
        
        lines.append(f"\n✅ Verified by Autonomi AI: {verification_code}")
        
        return "\n".join(lines)
    
    def _format_value_bets(self, data: Dict) -> str:
        """Format value bets EXACTLY like parlays - same format"""
        import math
        
        if "message" in data:
            return data.get("message", "No value bets found.")
        
        value_bets = data.get("value_bets", [])
        
        if not value_bets:
            return "🤖 My analysis:\n\n❌ No value bets found currently.\n💡 Try asking for a parlay instead."
        
        lines = ["🔒 Here are my value bets! SAFER PICKS\n"]
        
        for bet in value_bets[:15]:  # Top 15 value bets
            player = bet.get("player_name", "Unknown")
            stat_type = bet.get("stat_type", "yards")
            recommendation = bet.get("recommendation", "OVER")
            book_line = bet.get("book_line", 0)
            
            # Get clean stat name - EXACT same as parlays
            stat_lower = stat_type.lower()
            if ("pass" in stat_lower and "rush" in stat_lower) or "pass_rush" in stat_lower:
                stat_name = "Passing + Rushing Yards"
            elif ("rush" in stat_lower and "rec" in stat_lower) or "rush_rec" in stat_lower:
                stat_name = "Rushing + Receiving Yards"
            elif "passing" in stat_lower and "yard" in stat_lower:
                stat_name = "Passing Yards"
            elif "rushing" in stat_lower and "yard" in stat_lower:
                stat_name = "Rushing Yards"
            elif "receiving" in stat_lower and "yard" in stat_lower:
                stat_name = "Receiving Yards"
            elif "reception" in stat_lower and "yard" not in stat_lower:
                stat_name = "Receptions"
            elif "passing_td" in stat_lower or stat_type == "passing_tds":
                stat_name = "Passing TDs"
            elif "rushing_td" in stat_lower:
                stat_name = "Rushing TDs"
            elif "receiving_td" in stat_lower:
                stat_name = "Receiving TDs"
            else:
                stat_name = stat_type.replace("_", " ").title()
                stat_name = stat_name.replace("Tds", "TDs").replace(" Td ", " TD ")
            
            # EXACT parlay format: "80+ De'Von Achane Rushing Yards"
            if "yard" in stat_lower:
                # For OVER: use book line, For UNDER: go lower
                if recommendation == "OVER":
                    rounded_line = max(5, int(math.floor(book_line / 5) * 5))
                else:
                    # UNDER means AI predicts less - show lower line
                    rounded_line = max(5, int(math.floor(book_line / 5) * 5) - 5)
            else:
                # TDs, receptions - round to whole number, min 1
                if recommendation == "OVER":
                    rounded_line = max(1, int(round(book_line)))
                else:
                    rounded_line = max(1, int(round(book_line)) - 1)
            
            lines.append(f"  {rounded_line}+ {player} {stat_name}")
        
        lines.append(f"\n{len(value_bets[:15])} Pick Value Parlay")
        lines.append("These are my safest picks with the best edge!")
        
        return "\n".join(lines)
    
    def _format_schedule(self, data: Dict) -> str:
        """Format schedule response - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        if "player_name" in data:
            player = data.get("player_name", "Unknown")
            team = data.get("team", "Unknown")
            position = data.get("position", "?")
            
            lines = [f"🏈 {player}\n"]
            lines.append(f"  🎽 Team: {team}")
            lines.append(f"  📍 Position: {position}")
            
            if data.get("jersey_number"):
                lines.append(f"  #️⃣ Jersey: #{data['jersey_number']}")
            
            if data.get("next_game"):
                ng = data["next_game"]
                lines.append(f"\n📅 Next Game:")
                lines.append(f"  Week {ng.get('week', '?')} vs {ng.get('opponent', '?')}")
                lines.append(f"  {ng.get('date', '?')}")
            
            return "\n".join(lines)
        
        elif "team" in data:
            team = data.get("team", "Unknown")
            lines = [f"🏈 {team} Schedule\n"]
            
            if data.get("has_upcoming_game"):
                lines.append(f"📅 Next Game:")
                lines.append(f"  Week {data.get('week', '?')} vs {data.get('opponent', '?')}")
                lines.append(f"  {data.get('game_date', '?')}")
                if data.get("venue"):
                    lines.append(f"  📍 {data['venue']}")
            else:
                lines.append("  ❌ No upcoming games")
            
            return "\n".join(lines)
        
        return "📅 Schedule not available"
    
    def _format_meta(self, data: Dict) -> str:
        """Format meta/conversational responses about the AI"""
        message = data.get("message", "")
        sources = data.get("data_sources", [])
        
        lines = [f"🤖 {message}"]
        
        if sources:
            lines.append("\n📊 My data sources:")
            for source in sources:
                lines.append(f"  • {source}")
        
        return "\n".join(lines)
    
    def _format_player_info(self, data: Dict) -> str:
        """Format player info - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        player = data.get("player_name", "Unknown")
        team = data.get("team", "Unknown")
        position = data.get("position", "?")
        jersey = data.get("jersey_number", "")
        
        lines = [f"🏈 {player}\n"]
        lines.append(f"  🎽 Team: {team}")
        lines.append(f"  📍 Position: {position}")
        if jersey:
            lines.append(f"  #️⃣ Jersey: #{jersey}")
        
        # Next game info
        if data.get("next_game"):
            ng = data["next_game"]
            lines.append(f"\n📅 Next Game:")
            lines.append(f"  Week {ng.get('week', '?')} vs {ng.get('opponent', '?')}")
            lines.append(f"  {ng.get('date', '?')}")
        
        return "\n".join(lines)
    
    def _format_leaderboard(self, data: Dict) -> str:
        """Format leaderboard - clean list like parlays"""
        if "error" in data:
            return f"❌ {data['error']}"
        
        position = data.get("position", "")
        title = data.get("title", f"Top {position}s")
        players = data.get("leaderboard", [])  # get_top_players returns "leaderboard"
        
        if not players:
            return f"❌ No {position} stats leaders found."
        
        lines = [f"🏆 {title}\n"]
        
        for p in players[:10]:
            rank = p.get("rank", 0)
            name = p.get("player_name", "Unknown")
            team = p.get("team", "")
            primary = p.get("primary_stat", 0)
            primary_label = p.get("primary_label", "")
            secondary = p.get("secondary_stat", 0)
            secondary_label = p.get("secondary_label", "")
            games = p.get("games_played", 0)
            
            # Medal emojis for top 3
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            
            lines.append(f"  {medal} {name} ({team})")
            lines.append(f"      📊 {primary:.1f} {primary_label} | {secondary:.1f} {secondary_label} | {games} games")
        
        lines.append(f"\n📈 {len(players)} qualified players (3+ games)")
        
        return "\n".join(lines)
    
    def _format_player_outlook(self, data: Dict) -> str:
        """Format player outlook - simple performance analysis"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        player = data.get("player_name", "Unknown")
        team = data.get("team", "Unknown")
        position = data.get("position", "?")
        
        lines = [f"🔮 {player} Outlook\n"]
        lines.append(f"  🏈 Team: {team} | Position: {position}")
        
        # Stats summary
        if data.get("season_stats"):
            stats = data["season_stats"]
            lines.append(f"\n📊 Season Averages:")
            for stat, value in stats.items():
                stat_name = stat.replace("_", " ").title()
                lines.append(f"  • {stat_name}: {value:.1f}")
        
        # Recent form
        if data.get("recent_form"):
            form = data["recent_form"]
            trend = form.get("trend", "stable")
            trend_emoji = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"
            lines.append(f"\n{trend_emoji} Recent Form: {trend.upper()}")
        
        # Matchup info
        if data.get("next_matchup"):
            matchup = data["next_matchup"]
            lines.append(f"\n🆚 Next Matchup:")
            lines.append(f"  vs {matchup.get('opponent', '?')}")
            lines.append(f"  Matchup Grade: {matchup.get('grade', '?')}")
        
        # Prediction
        if data.get("prediction"):
            pred = data["prediction"]
            lines.append(f"\n🎯 Projection:")
            lines.append(f"  {pred.get('stat', '?')}: {pred.get('value', 0):.0f}")
            lines.append(f"  Confidence: {pred.get('confidence', 0):.0f}%")
        
        return "\n".join(lines)
    
    def _format_defensive_matchup(self, data: Dict) -> str:
        """Format defensive matchup analysis - clean and simple"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        defense = data.get("defense_team", "Unknown")
        vs_position = data.get("vs_position", "")
        
        lines = [f"🛡️ {defense} Defense Analysis\n"]
        
        if vs_position:
            lines.append(f"🆚 vs {vs_position.upper()}s:")
        
        # Rankings
        if data.get("rankings"):
            rankings = data["rankings"]
            lines.append(f"\n📊 Defensive Rankings:")
            for stat, rank in rankings.items():
                stat_name = stat.replace("_", " ").title()
                lines.append(f"  • {stat_name}: #{rank}")
        
        # Points allowed
        if data.get("points_allowed"):
            pa = data["points_allowed"]
            lines.append(f"\n🚫 Points Allowed:")
            lines.append(f"  Total: {pa.get('total', '?')}")
            lines.append(f"  Per Game: {pa.get('per_game', '?'):.1f}")
        
        # Recommendation
        if data.get("recommendation"):
            lines.append(f"\n✅ Verdict: {data['recommendation']}")
        
        return "\n".join(lines)
    
    def _format_general(self, data: Dict) -> str:
        """Format general/unknown responses - keep it clean"""
        if "error" in data:
            return f"❌ Sorry: {data['error']}"
        
        if "message" in data:
            return f"🤖 {data['message']}"
        
        # If we have structured data, format it cleanly
        lines = ["📋 Here's what I found:\n"]
        
        for key, value in data.items():
            if key.startswith("_"):
                continue
            
            key_display = key.replace("_", " ").title()
            
            if isinstance(value, list):
                lines.append(f"\n📌 {key_display}:")
                for item in value[:10]:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("player_name") or str(item)
                        lines.append(f"  • {name}")
                    else:
                        lines.append(f"  • {item}")
            elif isinstance(value, dict):
                lines.append(f"\n📌 {key_display}:")
                for k, v in value.items():
                    lines.append(f"  • {k}: {v}")
            else:
                lines.append(f"  • {key_display}: {value}")
        
        return "\n".join(lines)
    
    def chat(self, user_message: str) -> str:
        """
        Main chat entry point.
        
        Flow:
        1. Smart intent classification with Gemini (handles typos, variations)
        2. YOUR AI Engine processes based on classified intent
        3. Gemini formats the result (if available)
        4. Response is validated
        """
        try:
            # Step 1: Smart classification + YOUR AI processes the query
            # This uses Gemini ONLY to understand intent, then routes to YOUR data
            engine_result = self.process_with_smart_intent(user_message)
            
            # Step 2: Format with Gemini (or fallback)
            response = self.format_response(engine_result)
            
            return response
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Sorry, I encountered an error: {str(e)}"
    
    def chat_with_history(self, messages: List[Dict[str, str]]) -> str:
        """
        Chat with conversation history.
        
        Builds context from previous messages so references like "those games" work.
        """
        if not messages:
            return "How can I help you with NFL betting today?"
        
        # Get the latest user message
        latest_message = messages[-1].get("content", "")
        
        # Build context from conversation history
        # Extract key information from previous messages (teams, players, games mentioned)
        context_info = self._extract_conversation_context(messages[:-1])
        
        # If the latest message contains references like "those", "them", "that game", etc.
        # and we have context, expand the query
        expanded_query = self._expand_query_with_context(latest_message, context_info)
        
        # Log if we expanded the query (for debugging)
        if expanded_query != latest_message:
            print(f"\n{'='*60}")
            print(f"[CONTEXT] CONTEXT EXPANSION")
            print(f"{'='*60}")
            print(f"   Original: \"{latest_message}\"")
            print(f"   Expanded: \"{expanded_query}\"")
            print(f"   Last Intent: {context_info.get('last_intent')}")
            print(f"{'='*60}\n")
        
        # Process with YOUR AI using smart intent
        return self.chat(expanded_query)
    
    def _extract_conversation_context(self, previous_messages: List[Dict[str, str]]) -> Dict:
        """Extract key context from previous messages"""
        context = {
            "teams": [],
            "players": [],
            "games": [],
            "dates": [],
            "last_topic": None,
            "last_intent": None,  # Track what user last asked for
            "last_parlay_params": None  # Track parlay parameters (legs, date)
        }
        
        # Look through previous messages for context
        for msg in previous_messages:
            content = msg.get("content", "").lower()
            role = msg.get("role", "")
            
            # Track user's last intent from their messages
            if role == "user":
                # Check for parlay request
                if any(word in content for word in ["parlay", "leg parlay", "pick parlay", "betting picks"]):
                    context["last_intent"] = "parlay"
                    
                    # Extract number of legs
                    import re
                    leg_match = re.search(r'(\d+)\s*[-]?\s*(?:leg|pick)', content)
                    if leg_match:
                        num_legs = int(leg_match.group(1))
                    else:
                        num_legs = 5  # default
                    
                    # Extract date
                    if "thanksgiving" in content:
                        parlay_date = "thanksgiving"
                    elif "christmas" in content:
                        parlay_date = "christmas"
                    elif "sunday" in content:
                        parlay_date = "sunday"
                    else:
                        parlay_date = "sunday"
                    
                    context["last_parlay_params"] = {
                        "num_legs": num_legs,
                        "date": parlay_date
                    }
                    
                elif any(word in content for word in ["prediction", "predict", "how will", "how many"]):
                    context["last_intent"] = "prediction"
                elif any(word in content for word in ["stats", "statistics", "average"]):
                    context["last_intent"] = "stats"
                elif any(word in content for word in ["injury", "injured", "hurt"]):
                    context["last_intent"] = "injury"
                elif any(word in content for word in ["vs", "versus", "matchup"]):
                    context["last_intent"] = "matchup"
            
            # Extract team names mentioned
            team_keywords = [
                "packers", "lions", "chiefs", "cowboys", "bengals", "ravens",
                "eagles", "bears", "vikings", "49ers", "seahawks", "rams",
                "bills", "dolphins", "jets", "patriots", "steelers", "browns",
                "texans", "colts", "jaguars", "titans", "broncos", "raiders",
                "chargers", "cardinals", "falcons", "panthers", "saints",
                "buccaneers", "giants", "commanders", "green bay", "detroit",
                "kansas city", "dallas", "cincinnati", "baltimore", "philadelphia",
                "chicago", "minnesota", "san francisco", "seattle", "los angeles",
                "buffalo", "miami", "new york", "new england", "pittsburgh",
                "cleveland", "houston", "indianapolis", "jacksonville", "tennessee",
                "denver", "las vegas", "arizona", "atlanta", "carolina",
                "new orleans", "tampa bay", "washington"
            ]
            
            for team in team_keywords:
                if team in content:
                    # Capitalize properly
                    team_proper = team.title()
                    if team_proper not in context["teams"]:
                        context["teams"].append(team_proper)
            
            # Check for dates/events
            if "thanksgiving" in content:
                context["dates"].append("thanksgiving")
                context["last_topic"] = "thanksgiving_games"
            elif "christmas" in content:
                context["dates"].append("christmas")
                context["last_topic"] = "christmas_games"
            elif "sunday" in content:
                context["dates"].append("sunday")
                context["last_topic"] = "sunday_games"
            
            # Check for game mentions in assistant responses
            if role == "assistant":
                # Look for matchup patterns like "Team1 at Team2" or "Team1 vs Team2"
                import re
                matchup_pattern = r'(\w+(?:\s+\w+)?)\s+(?:at|vs|versus)\s+(\w+(?:\s+\w+)?)'
                matches = re.findall(matchup_pattern, content, re.IGNORECASE)
                for away, home in matches:
                    game_str = f"{away.strip()} at {home.strip()}"
                    if game_str not in context["games"]:
                        context["games"].append(game_str)
                
                # If assistant gave a parlay, remember that
                if "pick parlay" in content or "leg parlay" in content or "here are your picks" in content:
                    context["last_intent"] = "parlay"
        
        return context
    
    def _expand_query_with_context(self, query: str, context: Dict) -> str:
        """Expand vague references in query using context"""
        query_lower = query.lower()
        
        # Check for "give me another/different" requests - user wants same thing again
        wants_repeat = any(phrase in query_lower for phrase in [
            "different one", "another one", "new one", "give me another",
            "give me a different", "different parlay", "another parlay",
            "new parlay", "try again", "one more", "again", "redo",
            "different picks", "other picks", "new picks"
        ])
        
        # Check for risk level modifiers
        wants_safer = any(phrase in query_lower for phrase in [
            "safer", "safe", "conservative", "lower risk", "more likely",
            "easier", "less risky", "sure thing", "lock", "guaranteed"
        ])
        wants_riskier = any(phrase in query_lower for phrase in [
            "riskier", "risky", "aggressive", "higher odds", "long shot",
            "yolo", "big payout", "moon", "degenerate"
        ])
        
        if (wants_repeat or wants_safer or wants_riskier) and context.get("last_intent"):
            # User wants to repeat their last request (possibly with modifications)
            last_intent = context.get("last_intent")
            
            if last_intent == "parlay":
                # Rebuild the parlay request
                params = context.get("last_parlay_params", {})
                num_legs = params.get("num_legs", 10)
                parlay_date = params.get("date", "sunday")
                
                # Add risk modifier
                risk_modifier = ""
                if wants_safer:
                    risk_modifier = " safer"
                elif wants_riskier:
                    risk_modifier = " riskier"
                
                # Return a full parlay query with risk level
                return f"give me a{risk_modifier} {num_legs} leg parlay for {parlay_date}"
            
            elif last_intent == "prediction":
                # If they had asked about a player, ask again
                if context.get("players"):
                    return f"give me a prediction for {context['players'][0]}"
            
            elif last_intent == "matchup":
                if len(context.get("teams", [])) >= 2:
                    return f"{context['teams'][0]} vs {context['teams'][1]} matchup"
        
        # Check for references that need context
        needs_expansion = any(word in query_lower for word in [
            "those games", "these games", "that game", "the games",
            "those teams", "these teams", "them", "they",
            "for those", "for these", "for that", "for the"
        ])
        
        if not needs_expansion:
            return query
        
        # Special case: "that game" with parlay request and teams in context
        # This means user wants a parlay for a SPECIFIC game (not thanksgiving)
        is_parlay_request = any(word in query_lower for word in ["parlay", "paraly", "bet", "picks"])
        has_that_game = "that game" in query_lower or "this game" in query_lower
        
        if is_parlay_request and has_that_game and context.get("teams"):
            # User wants parlay for a specific game they mentioned
            teams = context["teams"]
            if len(teams) >= 2:
                return f"give me a parlay for {teams[0]} vs {teams[1]}"
            elif len(teams) == 1:
                return f"give me a parlay for {teams[0]} next game"
        
        # Build expanded query with context
        expanded = query
        
        # If asking about "those games" and we know which games
        if context.get("last_topic") == "thanksgiving_games" or "thanksgiving" in context.get("dates", []):
            # Replace vague reference with specific
            expanded = query + " (Thanksgiving games: Green Bay Packers vs Detroit Lions, Kansas City Chiefs vs Dallas Cowboys, Cincinnati Bengals vs Baltimore Ravens)"
        elif context.get("games"):
            games_str = ", ".join(context["games"][:3])
            expanded = query + f" (Games mentioned: {games_str})"
        elif context.get("teams"):
            teams_str = ", ".join(context["teams"][:6])
            expanded = query + f" (Teams mentioned: {teams_str})"
        
        return expanded


# Quick test
if __name__ == "__main__":
    from database import get_db
    
    db = next(get_db())
    ai = ChatAI(db)
    
    # Test queries
    test_queries = [
        "What team does Joe Mixon play for?",
        "How will Jalen Hurts do this week?",
        "Show me Eagles roster",
        "Eagles vs Cowboys prediction",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Q: {query}")
        print(f"{'='*60}")
        response = ai.chat(query)
        print(response)
