
import numpy as np
from numpy import mean
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error
from matplotlib import pyplot as plt
import xgboost as xgb
import seaborn as sb
from colorama import Fore, Style
import pickle
import sys
import datetime
import data_utils, model_utils


MODEL_FILE = 'my_model.sav'
START_YEAR = 2010
END_YEAR = 2022
GAME_DATA, PITCHER_DATA, BULLPEN_DATA = data_utils.get_data_dicts(START_YEAR, END_YEAR)
RUN_MAX = 9
FEATURE_LIST = [
    'temp',
    'has_DH',
    'stadium_score',
    'pregame_BA',
    'pregame_SLG',
    'recent_BA',
    'recent_SLG',
    'left/right_BA',
    'left/right_SLG',
    'home/away_BA',
    'home/away_SLG',
    'opp_starter_ERA',
    'opp_starter_WHIP',
    'opp_bullpen_ERA',
    'opp_bullpen_WHIP',
    'open_over_under',
    'Monday', 
    'Tuesday',
    'Wednesday', 
    'Thursday', 
    'Friday', 
    'Saturday', 
    'Sunday'
]

def make_game_sample(game, year, team, date):
    """
    Create and return an array of feature values. Values are added
    in the same order as listed in the FEATURE_LIST list. 

    When for_prediction is True, the opposing pitcher's stats are not 
    added, because the pitcher IDs are not known yet.
    """
    throw = 'right' if game['opp_starter_righty'] else 'left'
    loc = 'home' if game['home'] else 'away'
    home_team = team if game['home'] else game['opp']
    sample = []             
    sample.append(game['temp'])
    sample.append(data_utils.has_DH(home_team, year))
    sample.append(data_utils.get_stadium_score(team, game))
    sample.append(game['pregame_BA'])
    sample.append(game['pregame_SLG'])
    sample.append(game['10-day_BA'])
    sample.append(game['10-day_SLG'])
    sample.append(game[f'{throw}_BA'])
    sample.append(game[f'{throw}_SLG'])
    sample.append(game[f'{loc}_BA'])
    sample.append(game[f'{loc}_SLG'])
    sample.append(data_utils.get_pitcher_ERA(PITCHER_DATA, year, game['opp_starter_id'], date))
    sample.append(data_utils.get_pitcher_WHIP(PITCHER_DATA, year, game['opp_starter_id'], date))
    sample.append(data_utils.get_bullpen_ERA(BULLPEN_DATA, year, game['opp'], date))
    sample.append(data_utils.get_bullpen_WHIP(BULLPEN_DATA, year, game['opp'], date))
    sample.append(game['open_over_under'])
    sample.extend(data_utils.get_weekdays(date))
    return np.array(sample)


def is_incomplete_sample(date, game):
    """
    Return true if the game contains all of the necessary info
    for a full sample. 
    """
    if 'opp_starter_id' not in game or game['opp_starter_id'] == 'not_found':
        return True
    if 'pregame_BA' not in game:
        return True
    if 'open_over_under' not in game:
        return True
    if '10-day_BA' not in game or '15-day_BA' not in game:
        return True
    if game['home'] and 'home_BA' not in  game:
        return True
    if not game['home'] and 'away_BA' not in game:
        return True
    if game['opp_starter_righty'] and 'right_BA' not in game:
        return True
    if not game['opp_starter_righty'] and 'left_BA' not in game:
        return True
    year = date.split('-')[0]
    opp_pitcher_id = game['opp_starter_id'] 
    if opp_pitcher_id not in PITCHER_DATA[year]:
        return True
    if 'pregame_ERA' not in PITCHER_DATA[year][opp_pitcher_id][date]:
        return True
    opp = game['opp']
    if date not in BULLPEN_DATA[year][opp]:
        return True
    if 'pregame_ERA' not in BULLPEN_DATA[year][opp][date]:
        return True
    return False


def get_samples(test_years=[]):
    """
    Parse the game data and form data samples. Return 2d array of samples
    and a 1d array of targets.
    """
    incomplete = 0
    samples = []
    targets = []
    train_samples = []
    train_targets = []
    test_samples = []
    test_targets = []
    for year in GAME_DATA:
        for team in GAME_DATA[year]:
            for date in list(GAME_DATA[year][team])[1:]:
                game = GAME_DATA[year][team][date]
                team_runs = min(game['R'], RUN_MAX*9)
                if is_incomplete_sample(date, game):
                    incomplete += 1
                    continue
                sample = make_game_sample(game, year, team, date)
                samples.append(sample)
                targets.append(team_runs)
                if year not in test_years:
                    train_samples.append(sample)
                    train_targets.append(team_runs)
                else:
                    test_samples.append(sample)
                    test_targets.append(team_runs)

    df = pd.DataFrame(samples, columns=FEATURE_LIST)
    df['runs_scored'] = targets
    train_df = pd.DataFrame(train_samples, columns=FEATURE_LIST)
    train_df['runs_scored'] = train_targets
    test_df = pd.DataFrame(test_samples, columns=FEATURE_LIST)
    test_df['runs_scored'] = test_targets
    return df, train_df, test_df


def compare_to_vegas(rf, test_years=[], nearest_half=True):
    """
    """
    me_closer = 0
    vegas_closer = 0
    num_games = 0
    over_vegas = 0
    under_vegas = 0
    push_vegas = 0
    games = set()
    profit = 0
    games_bet = 0
    for year in test_years:
        for team in GAME_DATA[year]:
            for date in GAME_DATA[year][team]:
                game1 = GAME_DATA[year][team][date]
                opp = game1['opp']
                game2 = GAME_DATA[year][opp][date]
                home_team = team if game1['home'] else opp
                away_team = opp if home_team == team else team
                game_id = home_team + away_team + date
                # don't predict the same game twice
                if game_id in games:
                    continue
                if is_incomplete_sample(date, game1) or is_incomplete_sample(date, game2):
                    continue
                sample1 = make_game_sample(game1, year, team, date).reshape(1, len(FEATURE_LIST))
                sample2 = make_game_sample(game2, year, game1['opp'], date).reshape(1, len(FEATURE_LIST))

                prediction1 = float(rf.predict(sample1)[0])
                prediction2 = float(rf.predict(sample2)[0])

                prediction1 = model_utils.round_nearest_half(float(rf.predict(sample1)[0]))
                prediction2 = model_utils.round_nearest_half(float(rf.predict(sample2)[0]))
                my_total = round(prediction1 + prediction2, 2)

                if nearest_half:
                    my_total = model_utils.round_nearest_half(my_total)
                vegas_total = game1['open_over_under']
                actual_total = game1['R'] + game2['R']

                if my_total > vegas_total:
                    over_vegas += 1
                elif my_total < vegas_total:
                    under_vegas += 1
                else:
                    push_vegas += 1

                condition = True
                condition = abs(my_total - vegas_total) >= 1
                condition = my_total < vegas_total    
                if condition:
                    games_bet += 1
                    if abs(my_total - actual_total) < abs(vegas_total - actual_total):
                        me_closer += 1
                        profit += 10
                    elif abs(my_total - actual_total) > abs(vegas_total - actual_total):
                        vegas_closer += 1
                        profit -= 11

                num_games += 1
                games.add(game_id)

                # print(f'{team} vs {game1["opp"]} {date}')
                # print(f'My total:     {my_total}')
                # print(f'Vegas total:  {vegas_total}')
                # print(f'Actual score: {actual_total}', end='\n\n')

    success_rate = round(me_closer*100/(me_closer+vegas_closer), 2)
    success_color = Fore.GREEN if success_rate >= 50 else Fore.RED
    profit_color = Fore.GREEN if profit > 0 else Fore.RED
    years_display = test_years[0] if len(test_years) == 1 else test_years
    print('----------------------------')
    print(f'Model success {years_display}: {success_color}{success_rate}%{Style.RESET_ALL}\n')
    print(f'Profit ($10 units): {profit_color}{model_utils.format_dollars(profit)}{Style.RESET_ALL}')
    print(f'Games bet:   {round(games_bet*100/num_games)}% ({games_bet}/{num_games})')
    print(f'Over Vegas:  {round(over_vegas*100/num_games)}%')
    print(f'Under Vegas: {round(under_vegas*100/num_games)}%')
    print(f'Same:        {round(push_vegas*100/num_games)}%')


def develop(rf, df):
    """
    Function used to develop and test the model.
    """
    samples, targets = df.loc[:, df.columns!='runs_scored'], df['runs_scored']
    X_train, X_test, y_train, y_test = train_test_split(samples, targets)

    print('Performing cross-validation...')
    cv = KFold(n_splits=3, shuffle=True, random_state=42)
    train_scores = cross_val_score(rf, X_train, y_train, scoring='neg_root_mean_squared_error', cv=cv, n_jobs=-1)
    train_rmse = round(-1*mean(train_scores), 2)
    print(f'train RMSE: {train_rmse}')

    # score the test data
    rf.fit(X_train, y_train)
    predictions = rf.predict(X_test)
    test_rmse = round(mean_squared_error(y_test, predictions, squared=False), 2)
    print(f'test RMSE:  {test_rmse}')

    # create correlation heatmap
    plt.figure(figsize=(35, 35))
    heatmap = sb.heatmap(df.corr(), cmap='Blues', annot=True)
    plt.savefig('figures/correlation_heatmap.png')
    plt.close()

    # create feature importance chart
    importances = rf.feature_importances_
    sorted_indices = np.argsort(importances)[::-1]
    plt.bar(range(X_train.shape[1]), importances[sorted_indices], align='center')
    plt.xticks(range(X_train.shape[1]), X_train.columns[sorted_indices], rotation=90)
    plt.tight_layout()
    plt.savefig('figures/feature_importance.png')
    plt.close()


def fit_and_save(rf, df, filename):
    """
    """
    samples, targets = df.loc[:, df.columns!='runs_scored'], df['runs_scored']
    rf.fit(samples, targets)
    pickle.dump(rf, open(filename, 'wb'))
 

def test_each_year():
    """
    Creates a model for each year, trains the model on all other years,
    then reports accuracy for the given year. Essentially k-fold cross
    validation.
    """
    for year in [str(year) for year in range(START_YEAR, END_YEAR+1) if year != 2020]:
        rf = xgb.XGBRFRegressor(n_estimators=1000, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, reg_alpha=.1)
        test_years = [year]
        df, train_df, test_df = get_samples(test_years)
        X_train, y_train = train_df.loc[:, train_df.columns!='runs_scored'], train_df['runs_scored']
        rf.fit(X_train, y_train)
        compare_to_vegas(rf, test_years)


def get_most_recent_game(team):
    """
    """
    year = list(GAME_DATA)[-1]
    last_date = list(GAME_DATA[year][team])[-1]
    return GAME_DATA[year][team][last_date]


def predict(team, opp, date, team1_starter, team2_starter, vegas_total):
    """
    """
    year = date.split('-')[0]
    game1 = get_most_recent_game(team)
    game2 = get_most_recent_game(opp)

    if is_incomplete_sample(game1):
        print(f'Incomplete stats for {team}')
        return
    if is_incomplete_sample(game2):
        print(f'Incomplete stats for {opp}')
        return

    sample1 = make_game_sample(game1, team, date)
    sample2 = make_game_sample(game2, year, opp)
    team1_starter_id = data_utils.get_pitcher_ID(team, team1_starter)
    team2_starter_id = data_utils.get_pitcher_ID(team, team2_starter)
    # add_pitcher_stats_to_sample(sample1, date, team2_starter_id, opp)
    # add_pitcher_stats_to_sample(sample2, date, team1_starter_id, opp)
    sample1.append(vegas_total)
    sample2.append(vegas_total)

    model = pickle.load(MODEL_FILE)
    sample1 = sample1.reshape(1, len(FEATURE_LIST))
    sample2 = sample2.reshape(1, len(FEATURE_LIST))
    prediction1 = float(model.predict(sample1)[0])
    prediction2 = float(model.predict(sample2)[0])

    print(prediction1, prediction2)


def main():
    """
    """
    rf = xgb.XGBRFRegressor(n_estimators=1000, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, reg_alpha=.1)
    df, train_df, test_df = get_samples()

    args = sys.argv
    if '-d' in args or '-develop' in args:
        develop(rf, df)
    elif '-f' in args or '-fit' in args:
        fit_and_save(rf, df, MODEL_FILE)
    elif '-ty' in args or '-test-year' in args:
        if 'all' in args:
            test_each_year()
            return
        test_year = args[2]
        print(f'\nTesting model on {test_year}...\n')
        df, train_df, test_df = get_samples(test_years=[test_year])
        X_train, y_train = train_df.loc[:, train_df.columns!='runs_scored'], train_df['runs_scored']
        rf.fit(X_train, y_train)
        compare_to_vegas(rf, test_years=[test_year])


if __name__ == '__main__':
    main()