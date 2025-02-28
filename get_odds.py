
import pandas as pd
import datetime
import data_utils
from pybaseball import team_game_logs
import sys

TEAM_NAMES = {
    'LOS': 'LAD',
    'WAS': 'WSN',
    'SDG': 'SDP',
    'SFO': 'SFG',
    'CWS': 'CHW',
    'KAN': 'KCR',
    'CUB': 'CHC',
    'TAM': 'TBR'
}


def convert_team_name(name, year):
    """
    """
    if name == 'MIA' and int(year) < 2012:
        return 'FLA'
    elif name == 'FLA' and int(year) == 2012:
        return 'MIA'
    elif name in TEAM_NAMES:
        return TEAM_NAMES[name]
    return name


def get_date(row, year):
    """
    """
    month = int(str(row['Date'])[:-2])
    day = int(str(row['Date'])[-2:])
    return str(datetime.date(int(year), month, day))


def main():
    """
    """
    start_year = 2010
    end_year = 2022
    years = [str(year) for year in range(start_year, end_year+1) if year != 2020]
    game_data, pitcher_data, bullpen_data = data_utils.get_data_dicts(start_year, end_year)
    if 'l' in sys.argv or '-latest' in sys.argv:
        years = [datetime.date.today().year]

    for year in years:
        odds = pd.read_excel(f'vegas_odds/{year}.xlsx')
        df = pd.DataFrame(odds)
        games = set()
        for index, row in df.iterrows():
            opp_index = index+1 if index % 2 == 0 else index-1
            opp_row = df.iloc[opp_index]
            opp_team = convert_team_name(opp_row['Team'], year)
            team = convert_team_name(row['Team'], year)
            date = get_date(row, year)
            game_id = date + team + opp_team
            if game_id in games:
                date += ' (2)'
            games.add(game_id)

            # mostly playoff games
            if date not in game_data[year][team]:
                continue

            open_over_under = row['Open OU']
            open_ou_odds = row['Open OU Odds']
            close_over_under = row['Close OU']
            runs_scored = row['Final']
            game_runs = game_data[year][team][date]['R']
            if game_runs != runs_scored:
                # sometimes the double headers are not in chronological order
                if date + ' (2)' in game_data[year][team]:
                    date += ' (2)'
                elif ' (2)' in date:
                    date = date[:date.find('(')].strip()
                game_runs = game_data[year][team][date]['R']
                if runs_scored != game_runs:
                    print('MIXUP:', team, opp_team, date, f'-- [{team}]', 'me:', game_runs, 'vs odds sheet:', runs_scored)
            
            game_data[year][team][date]['open_over_under'] = open_over_under
            game_data[year][team][date]['close_over_under'] = close_over_under
            game_data[year][team][date]['open_ou_odds'] = open_ou_odds

        data_utils.dump_data(year, 'game-data.json', game_data[year])


if __name__ == '__main__':
    main()