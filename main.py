import os
import requests
import json
import bs4
import time
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv('LEAGUE_USERNAME')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def getData():
    try:
        url = f'https://www.leagueofgraphs.com/summoner/na/{USERNAME}'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
        response = requests.get(url , headers=headers)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        rank = soup.find_all('div', class_='leagueTier')[0].text
        rank = rank.strip()
        lp = soup.find_all('div', class_='league-points')[0].text
        lp = lp.strip()
        lp = int(lp.replace('LP: ', ''))
        win_loss = soup.find_all('div', class_='winslosses')[0].text
        win_loss = win_loss.strip()
        wins = win_loss.split('Wins: ')[1].split(' Losses: ')[0]
        losses = win_loss.split(' Losses: ')[1]
        wins = int(wins)
        losses = int(losses)
        total_games = wins + losses
        win_loss_ratio = wins / total_games
        win_loss_ratio = win_loss_ratio * 100
        win_loss_percent = round(win_loss_ratio, 2)
        last_game = soup.find_all('div', class_='victoryDefeatText')[0].text
        last_game = last_game.strip()
        url = f'https://www.leagueofgraphs.com/summoner/behavior/na/{USERNAME}'
        response = requests.get(url , headers=headers)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        matches_session = soup.find_all('div', class_='number solo-number')[0].text
        matches_session = matches_session.strip()
        matches_session = int(float(matches_session))
        return (rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
    except:
        return None

def writeData(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session):
    try:
        with open('data.json', 'w') as f:
            data_json = {
                'rank': rank,
                'lp': lp,
                'wins': wins,
                'losses': losses,
                'total_games': total_games,
                'win_loss_percent': win_loss_percent,
                'last_game': last_game,
                'matches_session': matches_session
            }
            json.dump(data_json, f)
        return
    except:
        return

def last_game_emoji(last_game):
    if last_game == 'Victory':
        return ':white_check_mark:'
    elif last_game == 'Defeat':
        return ':x:'
    else:
        return ':question:'

def sendWebhook(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session):
    try:
        webhook = {
            'content': None,
            'embeds': [
                {
                "title": "League of Graphs",
                "description": f"**__Current Season Stats__**\n\nCurrent Rank: **{rank}**\nCurrent League Points: **{lp}**\n\nTotal Games Played: **{total_games}**\nW - L : **{wins} 🥇** - **{losses} 😢**\nWin Rate: **{win_loss_percent}%**\n\nLast Game: **{last_game}** {last_game_emoji(last_game)}",
                "url": f"https://tracker.gg/lol/profile/riot/NA/{USERNAME}/overview?playlist=RANKED_SOLO_5x5",
                "color": None,
                }
            ],
            'attachments': []
        }
        json_data = json.dumps(webhook)
        headers = {'Content-Type': 'application/json'}
        url = WEBHOOK_URL
        requests.post(url, data=json_data, headers=headers)
        return
    except:
        return

def update():
    try:
        rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session = getData()

        # check if data.json exists
        if not (os.path.isfile('data.json')):
            writeData(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
            sendWebhook(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
            print(f"Current Stats - Rank: {rank} | LP: {lp} | Wins: {wins} | Losses: {losses} | Total Games: {total_games} | Win Loss Percent: {win_loss_percent}%")
            return

        with open('data.json', 'r') as f:
            data_json = json.load(f)
            # if json is empty
            if not data_json:
                writeData(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
                sendWebhook(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
                print(f"Current Stats - Rank: {rank} | LP: {lp} | Wins: {wins} | Losses: {losses} | Total Games: {total_games} | Win Loss Percent: {win_loss_percent}%")
                return
            # if json is different than current data
            if data_json['rank'] != rank or data_json['lp'] != lp or data_json['wins'] != wins or data_json['losses'] != losses or data_json['total_games'] != total_games or data_json['win_loss_percent'] != win_loss_percent or data_json['last_game'] != last_game or data_json['matches_session'] != matches_session:
                writeData(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
                sendWebhook(rank, lp, wins, losses, total_games, win_loss_percent, last_game, matches_session)
                print(f"Current Stats - Rank: {rank} | LP: {lp} | Wins: {wins} | Losses: {losses} | Total Games: {total_games} | Win Loss Percent: {win_loss_percent}%")
                return
    except:
        return



# loop update every minute
def loop():
    while True:
        try:
            update()
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except:
            continue

if __name__ == '__main__':
    loop()