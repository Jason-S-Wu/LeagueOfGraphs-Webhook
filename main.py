import os
import requests
import json
import bs4
import time
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('league_tracker.log'),
        logging.StreamHandler()
    ]
)

class LeagueStatsTracker:
    def __init__(self, summoner_name: str, region: str = 'na', webhook_url: str = None) -> None:
        self.summoner_name = summoner_name
        self.region = region
        self.base_url = 'https://www.leagueofgraphs.com/summoner'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
        }
        self.data_file = 'data.json'
        self.webhook_url = webhook_url
        
    def _get_profile_url(self) -> str:
        """Get the full profile URL for the summoner"""
        return f"{self.base_url}/{self.region}/{self.summoner_name}"

    def _get_behavior_url(self) -> str:
        """Get the full behavior URL for the summoner"""
        return f"{self.base_url}/behavior/{self.region}/{self.summoner_name}"

    def _make_request(self, url: str) -> Optional[bs4.BeautifulSoup]:
        """Make HTTP request with error handling and rate limiting"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return bs4.BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logging.error(f"Failed to fetch data from {url}: {str(e)}")
            return None

    def _extract_text(self, soup: bs4.BeautifulSoup, selector: str, class_name: str, index=0) -> Optional[str]:
        """Safely extract text from BeautifulSoup element"""
        try:
            element = soup.find_all(selector, class_=class_name)[index]
            return element.text.strip() if element else None
        except (IndexError, AttributeError) as e:
            logging.error(f"Failed to extract {class_name}: {str(e)}")
            return None

    def get_data(self) -> Optional[Tuple]:
        """Fetch and parse League of Legends stats"""
        try:
            profile_url = self._get_profile_url()
            soup = self._make_request(profile_url)
            if not soup:
                return None

            # Extract rank and LP
            rank = self._extract_text(soup, 'div', 'leagueTier')
            lp_text = self._extract_text(soup, 'div', 'league-points')
            
            if not rank or not lp_text:
                return None
                
            lp = int(lp_text.replace('LP: ', ''))

            # Extract wins and losses
            win_loss_text = self._extract_text(soup, 'div', 'winslosses')
            if not win_loss_text:
                return None
                
            wins_losses = win_loss_text.split('Wins: ')[1].split(' Losses: ')
            wins = int(wins_losses[0])
            losses = int(wins_losses[1])
            total_games = wins + losses
            win_loss_percent = round((wins / total_games * 100), 2) if total_games > 0 else 0

            # Extract last game result
            last_game = self._extract_text(soup, 'div', 'victoryDefeatText')
            if not last_game:
                return None

            # Get behavior data
            behavior_url = self._get_behavior_url()
            behavior_soup = self._make_request(behavior_url)
            if not behavior_soup:
                return None
                
            matches_session = self._extract_text(behavior_soup, 'div', 'number solo-number', 1)
            if not matches_session:
                return None

            return (rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
            
        except Exception as e:
            logging.error(f"Error in get_data: {str(e)}")
            return None

    def write_data(self, stats_data: Tuple) -> bool:
        """Write stats data to JSON file"""
        try:
            rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session = stats_data
            data_json = {
                'timestamp': datetime.now().isoformat(),
                'rank': rank,
                'lp': lp,
                'wins': wins,
                'losses': losses,
                'total_games': total_games,
                'win_loss_percent': win_loss_percent,
                'last_game': last_game,
                'matches_session': matches_session
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data_json, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error writing data: {str(e)}")
            return False

    def _get_emoji(self, last_game: str) -> str:
        """Get appropriate emoji for game result"""
        return {
            'Victory': ':white_check_mark:',
            'Defeat': ':x:'
        }.get(last_game, ':question:')

    def send_webhook(self, stats_data: Tuple) -> bool:
        """Send stats update to Discord webhook"""
        try:
            rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session = stats_data
            
            matches_session_hours = matches_session.split(' ')
            # get the days
            matches_session_hours[0] = matches_session_hours[0].replace('d', '')
            # get the hours
            matches_session_hours[1] = matches_session_hours[1].replace('h', '')
            # get the minutes
            matches_session_hours[2] = matches_session_hours[2].replace('m', '')
            matches_session_hours = int(matches_session_hours[0]) * 24 + int(matches_session_hours[1]) + int(matches_session_hours[2]) / 60
            # round to 2 decimal places
            matches_session_hours = round(matches_session_hours, 2)

            webhook_data = {
                'content': None,
                'embeds': [{
                    "title": f"{self.summoner_name} Check",
                    "description": (
                        f"**__Current Season Stats__**\n\n"
                        f"Current Rank: **{rank}**\n"
                        f"Current League Points: **{lp}**\n\n"
                        f"Total Games Played: **{total_games}**\n"
                        f"W - L : **{wins} 🥇** - **{losses} 😢**\n"
                        f"Win Rate: **{win_loss_percent}%**\n\n"
                        f"Last Game: **{last_game}** {self._get_emoji(last_game)}\n\n"
                        f"User has played a total of **{matches_session} ({matches_session_hours} h)** this season.\nThis is the equivalent of **{round(matches_session_hours * 2.5, 2)} miles** walked or **{round(matches_session_hours * 0.17, 2)} books** read or **{round(matches_session_hours * 0.57, 2)} movies** watched."
                    ),
                    "url": f"https://tracker.gg/lol/profile/riot/{self.region}/{self.summoner_name}/overview?playlist=RANKED_SOLO_5x5",
                    "color": None
                }],
                'attachments': []
            }

            response = requests.post(
                self.webhook_url,
                json=webhook_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logging.error(f"Error sending webhook: {str(e)}")
            return False

    def update(self) -> None:
        """Main update function to check for changes and update stats"""
        try:
            stats_data = self.get_data()
            if not stats_data:
                logging.warning("Failed to get current stats data")
                return

            # Check if data file exists and compare data
            if not os.path.isfile(self.data_file):
                self.write_data(stats_data)
                self.send_webhook(stats_data)
                logging.info(f"Initial stats written - Rank: {stats_data[0]} | LP: {stats_data[1]}")
                return

            try:
                with open(self.data_file, 'r') as f:
                    old_data = json.load(f)
            except json.JSONDecodeError:
                logging.error("Corrupted data file, overwriting")
                self.write_data(stats_data)
                self.send_webhook(stats_data)
                return

            # Compare relevant fields
            if any(old_data.get(key) != value for key, value in zip(
                ['rank', 'lp', 'wins', 'losses', 'total_games', 'win_loss_percent', 'last_game', 'matches_session'],
                stats_data
            )):
                self.write_data(stats_data)
                self.send_webhook(stats_data)
                logging.info(f"Stats updated - Rank: {stats_data[0]} | LP: {stats_data[1]}")

        except Exception as e:
            logging.error(f"Error in update function: {str(e)}")

def main():
    with open('config.json') as f:
        config = json.load(f)
    webhook = config['webhook']
    username = config['username']

    tracker = LeagueStatsTracker(summoner_name=username, webhook_url=webhook)
    logging.info("Starting League stats tracker...")
    
    while True:
        try:
            tracker.update()
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
