
from sportsipy.mlb.teams import Team, Teams
import pandas as pd
import sys
import calendar


class format:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'
   CHECK = u'\u2713'


TEAMS = ['ARI', 'ATL', 'BAL', 'BOS', 'CHC', 'CHW', 'CIN', 'CLE', 'COL', 'DET', 'FLA', 'HOU', 'KCR', 'LAA', 'LAD', 'MIL', 'MIN', 'NYM', 'NYY', 'OAK', 'PHI', 'PIT', 'SDP', 'SEA', 'SFG', 'STL', 'TBR', 'TEX', 'TOR', 'WSN']
MONTHS = {month:str(list(calendar.month_name).index(month)) for month in list(calendar.month_name) if month != ''}
YEARS = [year for year in range(2021, 2022)]
STAT_CATEGORIES = ['runs', 'at_bats', 'hits', 'home_runs', 'slugging_percentage', '*time_of_day']


def get_abbreviation(loc, box_score):
    """
    Return the abbreviaton for either the away or home team (specified by loc)
    from a given box score.
    """
    winner = box_score.winning_name
    home_name = box_score._home_name.text()
    away_name = box_score._away_name.text()
    if (loc == 'home' and home_name == winner) or (loc == 'away' and away_name == winner):
        return box_score.winning_abbr
    return box_score.losing_abbr


def format_date(date):
    """
    Formats a date from 'Saturday, May 8, 2021' to '2021-05-08'
    """
    vals = date.split(',')
    month, day = vals[1].strip().split()
    month = MONTHS[month]
    if len(month) == 1:
        month = '0' + month
    if len(day) == 1:
        day = '0' + day
    year = vals[2].strip()
    return f'{year}-{month}-{day}'


def add_game_stats(all_games, team_abbr, game):
    box_score = game.boxscore
    df = box_score.dataframe
    home_abbr = get_abbreviation('home', box_score)
    if team_abbr == home_abbr:
        loc  = 'home'
    else:
        loc = 'away'

    stats = {}
    for stat in STAT_CATEGORIES:
        key = f'{loc}_{stat}'
        if stat[0] == '*':
            key = stat[1:]
        stats[key] = df.iloc[0][key]
    date = format_date(box_score.date)

    if team_abbr not in all_games:
        all_games[team_abbr] = {}
    all_games[team_abbr][date] = stats


def should_skip(game):
    """
    Return true if the given game was the second game of a doubleheader,
    or if the game was less than 9 innings.
    """
    return game.game_number_for_day == 2 or game.innings < 9


def game_added(is_dh):
    """
    Prints '.' after a game has been added to the dictionary.
    Prints a ' ' for the second game of a doubleheader, which 
    isn't included as a datapoint.
    """
    if is_dh:
        sys.stdout.write('.')
    else:
        sys.stdout.write(' ')
    sys.stdout.flush()


def collect_data():
    """
    Collects box score data from every game and returns a DataFrame containing
    all of the relevant statistics

    all_games[team][date] = stats_dict
    """
    all_games = {}
    for year in YEARS:
        print('==========', year, '==========')
        for team_code in TEAMS[:2]:
            print(team_code, end='')
            team = Team(team_name=team_code, year=year)
            for game in team.schedule[:5]:
                if should_skip(game):
                    game_added(False)
                    continue
                add_game_stats(all_games, team.abbreviation, game)
                game_added(True)
            print(format.GREEN+format.CHECK+format.END)

    df = pd.DataFrame(all_games)
    df.index.name = 'Date'
    df = df.sort_index()
    return df


## --------------------- ##


def main():
    print(format.BOLD+'\nCollecting game data...\n'+format.END)
    df = collect_data()
    df.to_csv('./data.csv', na_rep=' --- ')


if __name__ == '__main__':
    main()


