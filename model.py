
import numpy as np
from numpy import mean
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV, cross_val_score, KFold
from sklearn.feature_selection import RFECV
from sklearn.linear_model import LinearRegression
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_squared_error
from matplotlib import pyplot as plt
import xgboost as xgb
import seaborn as sb
from colorama import Fore, Style
import pickle
import json
import datetime
import sys
import data_utils, model_utils


GAME_DATA, PITCHER_DATA, BULLPEN_DATA = data_utils.get_data_dicts()
RUN_MAX = 100


FEATURE_LIST = [
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
    'stadium_score',
    'temp',
]


def is_incomplete_sample(date, game):
    """
    Return true if the game contains all of the necessary info
    for a full sample. 
    """
    if game['R'] > RUN_MAX:
        return True
    if 'opp_starter_id' not in game or game['opp_starter_id'] == 'not_found':
        return True
    if 'pregame_BA' not in game:
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


def add_hitting_stats(key, sample, game):
    """
    Adds hitting data to the given sample. The split to 
    add is specified by the key.
    """
    if key == 'opp_starter_righty':
        split = 'right' if game[key] else 'left'
    elif key == 'home':
        split = 'home' if game[key] else 'away'
    else:
        split = key
    sample.append(game[f'{split}_BA'])
    sample.append(game[f'{split}_SLG'])


def get_samples():
    """
    Parse the game data and form data samples. Return 2d array of samples
    and a 1d array of targets.
    """
    print('Gathering samples...')
    all_samples = []
    targets = []
    count = 0
    for year in GAME_DATA:
        for team in GAME_DATA[year]:
            for date in list(GAME_DATA[year][team])[1:]:
                game = GAME_DATA[year][team][date]
                if is_incomplete_sample(date, game):
                    count += 1
                    continue
                sample = []
                add_hitting_stats('pregame', sample, game)
                add_hitting_stats('10-day', sample, game)
                add_hitting_stats('opp_starter_righty', sample, game)
                add_hitting_stats('home', sample, game)
                sample.append(model_utils.get_pitcher_ERA(PITCHER_DATA, year, game['opp_starter_id'], date))
                sample.append(model_utils.get_pitcher_WHIP(PITCHER_DATA, year, game['opp_starter_id'], date))
                sample.append(model_utils.get_bullpen_ERA(BULLPEN_DATA, year, game['opp'], date))
                sample.append(model_utils.get_bullpen_WHIP(BULLPEN_DATA, year, game['opp'], date))
                sample.append(model_utils.get_stadium_score(team, game))
                sample.append(game['temp'])

                all_samples.append(sample)
                targets.append(game['R'])

    print(f'{Style.DIM}{len(all_samples)} complete samples.')
    print(f'{count} incomplete samples.\n{Style.RESET_ALL}')
    df = pd.DataFrame(all_samples, columns=FEATURE_LIST)
    return df, np.array(targets)


def run_grid_search(param_grid, samples, targets):
    """
    Performs GridSearchCV for the best hyperparameters for XGBRFRegressor.
    Prints the best parameters and RMSE train/test values.
    """
    X_train, X_test, y_train, y_test = train_test_split(samples, targets)

    rf = xgb.XGBRFRegressor(n_estimators=1000, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, colsample_bytree=.8, reg_alpha=.1)
    tuned_rf = GridSearchCV(rf, param_grid, n_jobs=-1, scoring='neg_root_mean_squared_error')
    tuned_rf.fit(X_train, y_train)
    predictions = tuned_rf.best_estimator_.predict(X_test)
    train_rmse = round(tuned_rf.best_score_*-1, 3)
    test_rmse = -1*round(tuned_rf.score(X_test, y_test), 3)
    print(f'Best estimators:    {tuned_rf.best_params_}')
    print(f'Best training rmse: {train_rmse}')
    print(f'Test rmse:          {test_rmse}')


def main():
    """
    """
    samples, targets = get_samples()
    X_train, X_test, y_train, y_test = train_test_split(samples, targets)

    # initialize random forest and get training score
    rf = xgb.XGBRFRegressor(n_estimators=100, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, colsample_bytree=.8, reg_alpha=.1)
    cv = KFold(n_splits=3, shuffle=True, random_state=42)
    train_scores = cross_val_score(rf, X_train, y_train, scoring='neg_root_mean_squared_error', cv=cv, n_jobs=-1)
    train_rmse = round(-1*mean(train_scores), 2)
    print(f'train RMSE: {train_rmse}')

    # score the test data
    rf.fit(X_train, y_train)
    predictions = rf.predict(X_test)
    test_rmse = round(mean_squared_error(y_test, predictions, squared=False), 2)
    print(f'test RMSE:  {test_rmse}')

    # compare to previous models
    best_log = model_utils.best_model_log()
    if test_rmse < best_log['best_rmse']:
        model_utils.set_best_model(test_rmse, RUN_MAX, FEATURE_LIST)
        print(Fore.GREEN+'New best model!'+Style.RESET_ALL)

    # create correlation heatmap
    samples['runs_scored'] = targets
    plt.figure(figsize=(35, 35))
    heatmap = sb.heatmap(samples.corr(), cmap='Blues', annot=True)
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


if __name__ == '__main__':
    main()