
from bs4 import BeautifulSoup
import requests
import datetime
import sys, os, time
from colorama import Fore, Style
import data_utils


GAME_DATA = 'game-data.json'
PITCHER_DATA = 'pitcher-data.json'
BULLPEN_DATA = 'team-bullpen-data.json'

START_YEAR = 2010
END_YEAR = 2021
TODAY = datetime.date.today()

PITCHING_STATS = ['IP', 'ER', 'H', 'BB']
HITTING_STATS = ['AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'HBP', 'SF', 'postgame_BA', 'postgame_OBP', 'postgame_SLG', 'postgame_OPS']
GAME_STATS = ['date', 'home', 'opp', 'opp_starter_righty', 'opp_starter']
ALL_STATS = GAME_STATS + HITTING_STATS

SESSION = requests.Session()


def remove_headers(soup):
    """
    Removes the repetitive stat headers that occur throughout the season table
    """
    headers = soup.find_all('tr', class_='thead')
    for header in headers:
        header.extract()


def add_yesterday_off(box_score, season_games):
    """
    Adds whether or not the specified team had an off day.
    """
    date = data_utils.str_to_datetime(box_score['date'])
    day_before = data_utils.get_day_before(date)
    box_score['yesterday_off'] = int(day_before not in season_games)
    return box_score


def add_is_night_game(season_games, team_abbr, date, is_night):
    """
    Adds whether or not the game is at night for both teams for a given game. 
    """
    opp_abbr = season_games[team_abbr][date]['opp']
    season_games[team_abbr][date]['night'] = is_night
    season_games[opp_abbr][date]['night'] = is_night


def parse_pitcher_stats(line):
    """
    Parse a line in the boxscore page for pitcher stats. Return a map of each 
    pitcher's stats for that game.
    """
    csv = line.find('data-append-csv="')+17
    player_id = line[csv : line.find('"', csv)].strip()
    shtml = line.find('.shtml')
    player_name = line[line.find('>', shtml)+1:line.find('<', shtml)].strip()
    game_stats = {
        'name': player_name,
        'id': player_id, 
    }
    for stat in PITCHING_STATS:
        i = line.find(f'data-stat="{stat}"')
        num = float(line[line.find('>', i)+1:line.find('<', i)].strip())
        game_stats[stat] = num
    
    return game_stats


def add_pitcher_stats(stats, team, opp, date, season_pitching, season_games):
    """
    Adds a pitcher's game stats to the dictionary containing all of the pitcher
    data. pitcher_data dict in the form of:

    pitcher_data['verlaju01'] = {'2015-05-13': {stats}, '2015-05-18': {stats}}

    Also adds the starter's player_id to dictionary of season games, under the 
    appropriate game for the starter's opponent.
    """
    player_id = stats['id']
    if player_id not in season_pitching:
        season_pitching[player_id] = {}

    # create new appearance for the pitcher
    season_pitching[player_id][date] = {
        'team': team,
         'opp': opp,
    }
    # load the pitcher's stats into the dict
    for category in PITCHING_STATS:
        season_pitching[player_id][date][category] = stats[category]

    # add the pitcher info to the data for the opponent's game
    game = season_games[opp][date]
    if 'opp_starter_id' not in game:
        game['opp_starter_id'] = player_id
    if 'opp_pitchers' not in game:
        game['opp_pitchers'] = []
    game['opp_pitchers'].append(player_id)


def get_bullpen_stats(season_games, pitcher_data, team_abbr, year):
    """
    Calculate ERA and WHIP for a team's bullpen prior to the start of each game
    and return a map containing the information. 

    team_bullpen['2021-07-19'] = {'pregame_ERA': 3.48, ...}
    """
    print(f'{data_utils.BACKSPACE*6} {team_abbr} {data_utils.CHECK}', end='', flush=True)
    game_page = SESSION.get(f'https://www.baseball-reference.com/teams/tgl.cgi?team={team_abbr}&t=p&year={year}').text
    soup = BeautifulSoup(game_page, 'lxml')
    remove_headers(soup)
    season = soup.find('div', id='div_team_pitching_gamelogs').find_all('tr')[1:]

    season_ER, season_BB, season_H, season_IP = (0, 0, 0, 0)
    team_bullpen = {}
    for game in season:
        if data_utils.game_suspended(game):
            continue
        date = data_utils.get_stat_value(game, 'date_game')
        if date in team_bullpen:
            date += ' (2)'
        opp_abbr = data_utils.get_stat_value(game, 'opp_ID')

        # game was suspended but baseball-reference mistakenly doesn't have it marked 
        if date not in season_games[opp_abbr] or date not in season_games[team_abbr]:
            continue
        # game page did not list a starting pitcher
        if season_games[opp_abbr][date]['opp_starter_id'] == 'not_found':
            continue

        starter_id = season_games[opp_abbr][date]['opp_starter_id']
        last_name = season_games[opp_abbr][date]['opp_starter'].split('.')[-1]
        full_name = season_games[opp_abbr][date]['opp_starter_name']
        # starting pitcher disagreement between game log and recap page
        if not data_utils.starter_verified(last_name, full_name):
            continue

        starter_stats = pitcher_data[starter_id][date]
        game_H = data_utils.get_stat_value(game, 'H') - starter_stats['H']
        game_IP = data_utils.add_IP(data_utils.get_stat_value(game, 'IP'), -starter_stats['IP'])
        game_BB = data_utils.get_stat_value(game, 'BB') - starter_stats['BB']
        game_ER = data_utils.get_stat_value(game, 'ER') - starter_stats['ER']

        team_bullpen[date] = {
            'game_H': game_H,
            'game_IP': game_IP,
            'game_ER': game_ER,
            'game_BB': game_BB,
        }
        if season_IP > 0:
            team_bullpen[date]['pregame_ERA'] = data_utils.calculate_ERA(season_ER, season_IP)
            team_bullpen[date]['pregame_WHIP'] = data_utils.calculate_WHIP(season_IP, season_BB, season_H)

        season_H += game_H
        season_IP = data_utils.add_IP(season_IP, game_IP)
        season_BB += game_BB
        season_ER += game_ER

    return team_bullpen


def calculate_pitcher_stats(pitcher_data):
    """
    Calculates WHIP and ERA for each starter as the season goes on, as well
    as WHIP and ERA for each team's bullpen.
    """
    for pitcher in pitcher_data:
        season_IP, season_ER, season_BB, season_H = (0, 0, 0, 0)
        appearences = pitcher_data[pitcher]
        for date in appearences:
            game = appearences[date]
            if season_IP > 0:
                game['pregame_ERA'] = data_utils.calculate_ERA(season_ER, season_IP)
                game['pregame_WHIP'] = data_utils.calculate_WHIP(season_IP, season_BB, season_H)
            season_ER += game['ER']
            season_BB += game['BB']
            season_H += game['H']
            season_IP = data_utils.add_IP(season_IP, game['IP'])
    print(data_utils.DONE)


def calculate_offensive_stats(season_games):
    """
    Calculates offensive statistics (BA, SLG, OBP, OPS) for a team's:
    - last n-games
    - season home/away splits
    - season splits for when a RHP starts vs when a LHP starts
    and and adds the statistics to the json map of game data.
    """
    for team in season_games:
        # initialize stats for a team's season splits - home/away, games against RHP starters vs LHP starters
        home_H, home_AB, home_BB, home_SF, home_HBP, home_1B, home_2B, home_3B, home_HR = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        away_H, away_AB, away_BB, away_SF, away_HBP, away_1B, away_2B, away_3B, away_HR = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        left_H, left_AB, left_BB, left_SF, left_HBP, left_1B, left_2B, left_3B, left_HR = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        right_H, right_AB, right_BB, right_SF, right_HBP, right_1B, right_2B, right_3B, right_HR = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        dates = list(season_games[team])
        first_game = season_games[team][dates[0]]
        if first_game['home']:
            home_H = first_game['H']
            home_AB = first_game['AB']
            home_BB = first_game['BB']
            home_SF = first_game['SF']
            home_HBP = first_game['HBP']
            home_1B = first_game['H']-(first_game['2B']+first_game['3B']+first_game['HR'])
            home_2B = first_game['2B']
            home_3B = first_game['3B']
            home_HR = first_game['HR']
        else:
            away_H = first_game['H']
            away_AB = first_game['AB']
            away_BB = first_game['BB']
            away_SF = first_game['SF']
            away_HBP = first_game['HBP']
            away_1B = first_game['H']-(first_game['2B']+first_game['3B']+first_game['HR'])
            away_2B = first_game['2B']
            away_3B = first_game['3B']
            away_HR = first_game['HR']

        if first_game['opp_starter_righty']:
            right_H = first_game['H']
            right_AB = first_game['AB']
            right_BB = first_game['BB']
            right_SF = first_game['SF']
            right_HBP = first_game['HBP']
            right_1B = first_game['H']-(first_game['2B']+first_game['3B']+first_game['HR'])
            right_2B = first_game['2B']
            right_3B = first_game['3B']
            right_HR = first_game['HR']
        else:
            left_H = first_game['H']
            left_AB = first_game['AB']
            left_BB = first_game['BB']
            left_SF = first_game['SF']
            left_HBP = first_game['HBP']
            left_1B = first_game['H']-(first_game['2B']+first_game['3B']+first_game['HR'])
            left_2B = first_game['2B']
            left_3B = first_game['3B']
            left_HR = first_game['HR']

        # loop through all of the games, starting with the second game
        for i in range(1, len(dates)):
            date = dates[i]
            game = season_games[team][date]
            prev_game = season_games[team][dates[i-1]]

            game['pregame_BA'] = prev_game['postgame_BA']
            game['pregame_OBP'] = prev_game['postgame_OBP']
            game['pregame_SLG'] = prev_game['postgame_SLG']
            game['pregame_OPS'] = prev_game['postgame_OPS']

            if home_AB > 0:
                game['home_BA'] = data_utils.calculate_BA(home_AB, home_H)
                game['home_OBP'] = data_utils.calculate_OBP(home_H, home_BB, home_HBP, home_AB, home_SF)
                game['home_SLG'] = data_utils.calculate_SLG(home_1B, home_2B, home_3B, home_HR, home_AB)
                game['home_OPS'] = data_utils.calculate_OPS(game['home_OBP'], game['home_SLG'])
            if away_AB > 0:
                game['away_BA'] = data_utils.calculate_BA(away_AB, away_H)
                game['away_OBP'] = data_utils.calculate_OBP(away_H, away_BB, away_HBP, away_AB, away_SF)
                game['away_SLG'] = data_utils.calculate_SLG(away_1B, away_2B, away_3B, away_HR, away_AB)
                game['away_OPS'] = data_utils.calculate_OPS(game['away_OBP'], game['away_SLG'])
            if right_AB > 0:
                game['right_BA'] = data_utils.calculate_BA(right_AB, right_H)
                game['right_OBP'] = data_utils.calculate_OBP(right_H, right_BB, right_HBP, right_AB, right_SF)
                game['right_SLG'] = data_utils.calculate_SLG(right_1B, right_2B, right_3B, right_HR, right_AB)
                game['right_OPS'] = data_utils.calculate_OPS(game['right_OBP'], game['right_SLG'])
            if left_AB > 0:
                game['left_BA'] = data_utils.calculate_BA(left_AB, left_H)
                game['left_OBP'] = data_utils.calculate_OBP(left_H, left_BB, left_HBP, left_AB, left_SF)
                game['left_SLG'] = data_utils.calculate_SLG(left_1B, left_2B, left_3B, left_HR, left_AB)
                game['left_OPS'] = data_utils.calculate_OPS(game['left_OBP'], game['left_SLG'])

            if game['home']:
                home_H += game['H']
                home_AB += game['AB']
                home_BB += game['BB']
                home_SF += game['SF']
                home_HBP += game['HBP']
                home_1B += game['H']-(game['2B']+game['3B']+game['HR'])
                home_2B += game['2B']
                home_3B += game['3B']
                home_HR += game['HR']
            else:              
                away_H += game['H']
                away_AB += game['AB']
                away_BB += game['BB']
                away_SF += game['SF']
                away_HBP += game['HBP']
                away_1B += game['H']-(game['2B']+game['3B']+game['HR'])
                away_2B += game['2B']
                away_3B += game['3B']
                away_HR += game['HR']
            if game['opp_starter_righty']:
                right_H += game['H']
                right_AB += game['AB']
                right_BB += game['BB']
                right_SF += game['SF']
                right_HBP += game['HBP']
                right_1B += game['H']-(game['2B']+game['3B']+game['HR'])
                right_2B += game['2B']
                right_3B += game['3B']
                right_HR += game['HR']
            else:
                left_H += game['H']
                left_AB += game['AB']
                left_BB += game['BB']
                left_SF += game['SF']
                left_HBP += game['HBP']
                left_1B += game['H']-(game['2B']+game['3B']+game['HR'])
                left_2B += game['2B']
                left_3B += game['3B']
                left_HR += game['HR']

            # collect stats from last n games
            for n in [10, 15]:
                recent_H, recent_AB, recent_BB, recent_SF, recent_HBP, recent_1B, recent_2B, recent_3B, recent_HR = 0, 0, 0, 0, 0, 0, 0, 0, 0
                for j in range(1, n+1):
                    if i-j < 0:
                        break
                    prev_date = dates[i-j]
                    prev_game = season_games[team][prev_date]
                    recent_H += prev_game['H']
                    recent_AB += prev_game['AB']
                    recent_BB += prev_game['BB']
                    recent_SF += prev_game['SF']
                    recent_HBP += prev_game['HBP']
                    recent_1B += prev_game['H']-(prev_game['2B']+prev_game['3B']+prev_game['HR'])
                    recent_2B += prev_game['2B']
                    recent_3B += prev_game['3B']
                    recent_HR += prev_game['HR']

                game[f'{n}-day_BA'] = data_utils.calculate_BA(recent_AB, recent_H)
                game[f'{n}-day_OBP'] = data_utils.calculate_OBP(recent_H, recent_BB, recent_HBP, recent_AB, recent_SF)
                game[f'{n}-day_SLG'] = data_utils.calculate_SLG(recent_1B, recent_2B, recent_3B, recent_HR, recent_AB)
                game[f'{n}-day-OPS'] = data_utils.calculate_OPS(game[f'{n}-day_OBP'], game[f'{n}-day_SLG'])

    print(data_utils.DONE)


def get_season_pitching(year, season_games):
    """
    Scrape all of the desired pitching data from the given year and load it into
    a dictionary containing all of the stats into a json file. Also add some 
    information about the game like temperature and time.
    """
    schedule_page = SESSION.get(f'https://www.baseball-reference.com/leagues/majors/{year}-schedule.shtml').text
    soup = BeautifulSoup(schedule_page, 'lxml')
    schedule = soup.find_all('p', class_='game')
    
    season_pitching = {}
    for game in schedule:
        game_id = game.select('a')[2].get('href')
        if data_utils.has_not_happened(game_id):
            break
        game_page = SESSION.get('https://www.baseball-reference.com/' + game_id).text
        soup = BeautifulSoup(game_page, 'lxml')
        if data_utils.is_playoffs(soup):
            break
        if data_utils.was_suspended(soup):
            continue

        date, away_abbr, home_abbr = data_utils.parse_title(soup.title.text)
        if data_utils.is_second_game(soup):
            date += ' (2)'

        away_starter, home_starter = data_utils.get_starting_pitchers(soup)
        season_games[away_abbr][date]['opp_starter_name'] = home_starter[0]
        season_games[away_abbr][date]['opp_starter_id'] = home_starter[1]
        season_games[home_abbr][date]['opp_starter_name'] = away_starter[0]
        season_games[home_abbr][date]['opp_starter_id'] = away_starter[1]

        # add details/features that are found on this page (night, temp)
        night_game = data_utils.get_night_game(soup)
        temp = data_utils.get_temperature(soup)
        season_games[home_abbr][date]['night_game'] = night_game
        season_games[away_abbr][date]['night_game'] = night_game
        season_games[home_abbr][date]['temp'] = temp
        season_games[away_abbr][date]['temp'] = temp

        team = away_abbr
        opp = home_abbr
        team_totals = 0
        # find and add each pitcher's stats
        for line in game_page.split('\n'):
            if team_totals == 2:
                break
            if not data_utils.is_pitching_row(line):
                continue
            if data_utils.has_team_totals(line):
                team = home_abbr
                opp = away_abbr
                team_totals += 1
                continue
            stats = parse_pitcher_stats(line)
            add_pitcher_stats(stats, team, opp, date, season_pitching, season_games)
        data_utils.print_same_line(f'{date} - {away_abbr} @ {home_abbr} {data_utils.CHECK}')

    return season_pitching


def get_season_offense(team_abbr, year):
    """
    Adds a team's desired boxscore values for each game in the specified season.
    Adds the desired stats from each row listed here: 
    https://www.baseball-reference.com/teams/tgl.cgi?team=BOS&t=b&year=2021'
    """
    season_page = SESSION.get(f'https://www.baseball-reference.com/teams/tgl.cgi?team={team_abbr}&t=b&year={year}').text
    soup = BeautifulSoup(season_page, 'lxml')
    remove_headers(soup)
    table = soup.find(id='team_batting_gamelogs').find_all('tr')[1:]

    count = 0
    season_games = {}
    for row in table:
        if data_utils.game_suspended(row):
            continue
        box_score = {}
        for stat in ALL_STATS:
            box_score[stat] = data_utils.get_stat_value(row, stat)
        add_yesterday_off(box_score, season_games)
        date = box_score['date']
        if date in season_games:
            date += ' (2)'
        season_games[date] = box_score
        count += 1
    data_utils.print_same_line(f'{team_abbr} ({count} games) {data_utils.CHECK}')

    return season_games


def get_data(years):
    """
    Collect and calculate the necessary data from every year in 
    the years list.
    """
    for year in years:
        print(f'\n====================== {year} ======================')

        # get hitting data
        season_games = {}
        print(f'\nScraping{Style.BRIGHT} [hitting] {Style.RESET_ALL}data:')
        teams = data_utils.get_team_abbreviations(year)
        for team_abbr in teams:
            season_games[team_abbr] = get_season_offense(team_abbr, year)
        print('Calculating offensive stats...', flush=True, end=' ')
        calculate_offensive_stats(season_games)

        # get pitching data
        print(f'\nScraping{Style.BRIGHT} [pitching] {Style.RESET_ALL}data:')
        pitcher_data = get_season_pitching(year, season_games)
        print(f'Gathering each team\'s bullpen stats...', end='      ', flush=True)
        bullpen_data = {}
        for team_abbr in teams:
            bullpen_data[team_abbr] = get_bullpen_stats(season_games, pitcher_data, team_abbr, year)
        print(data_utils.BACKSPACE*5+data_utils.DONE)
        print('Calculating pitching stats...', flush=True, end=' ')
        calculate_pitcher_stats(pitcher_data)

         # create folder and dump the data
        if not os.path.isdir(f'data/{year}'):
            os.mkdir(f'data/{year}')
        data_utils.dump_data(year, BULLPEN_DATA, bullpen_data)
        data_utils.dump_data(year, PITCHER_DATA, pitcher_data)
        data_utils.dump_data(year, GAME_DATA, season_games)


def main():
    """
    Run the functions to scrape the data. 
    """
    allowed_args = ['-update', '-u', '-year']
    args = sys.argv[1:]
    for arg in args:
        if arg not in allowed_args:
            print(f'Invalid argument: {arg}')
            return
    
    years = [str(year) for year in range(START_YEAR, END_YEAR+1) if year != 2020]
    update = False
    if '-update' in args or '-u' in args:
        update = True
        years = [TODAY.year]
    elif '-year' in args:
        years = [args[args.index('-year')+1]]

    if update:
        yesterday = data_utils.get_day_before(TODAY)
        latest = data_utils.format_date_long(yesterday)
        print(f'\nPulling {years[0]} data through {Style.BRIGHT+latest+Style.RESET_ALL}...')
        get_data(years)
        print(f'\nData through {latest} {Fore.GREEN+Style.BRIGHT}succesfully updated.{Style.RESET_ALL}\n')
        return

    time_period = Style.BRIGHT + (str(years[0]) if len(years) == 1 else f'{years[0]}-{years[-1]}') + Style.RESET_ALL
    run = input(f'\nScrape MLB game data from {time_period}? This will take some time. (y/n) ')
    if run.lower().strip() == 'y':  
        get_data(years)
        print(f'\nData from {time_period}{Fore.GREEN+Style.BRIGHT} succesfully scraped.{Style.RESET_ALL}\n')


if __name__ == '__main__':
    main()