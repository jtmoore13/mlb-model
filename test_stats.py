
import random as rand
import utils
import get_data


GAME_DATA = {}
PITCHER_DATA = {}
BULLPEN_DATA = {}
for year in utils.YEARS:    
    GAME_DATA[year] = utils.load_data(year, get_data.GAME_DATA)
    PITCHER_DATA[year] = utils.load_data(year, get_data.PITCHER_DATA)
    BULLPEN_DATA[year] = utils.load_data(year, get_data.BULLPEN_DATA)


def test_num_teams():
    """
    Tests that all 30 teams are accounted for.
    """
    for year in utils.YEARS:
        assert(len(GAME_DATA[year]) == 30)
        assert(len(BULLPEN_DATA[year]) == 30)


def test_num_games():
    """
    Test that the number of games is above ~155
    """
    for year in utils.YEARS:
        for team in BULLPEN_DATA[year]:
            assert(len(BULLPEN_DATA[year][team]) > 155)
        for team in GAME_DATA[year]:
            assert(len(GAME_DATA[year][team]) > 155)



# =========================== OFFENSIVE TESTS =========================== #


def test_game_keys():
    """
    Tests that all necessary fields are present in each game.
    """
    for year in GAME_DATA:
        data = GAME_DATA[year]
        for team in data:
            dates = list(data[team])
            for i in range(len(dates)):
                date = dates[i]
                keys = list(data[team][date])
                if i > 0:
                    assert('pregame_BA' in keys)
                    assert('pregame_OBP' in keys)
                    assert('pregame_OPS' in keys)
                    assert('pregame_SLG' in keys)
                assert('date' in keys)
                assert('home' in keys)
                assert('opp' in keys)
                assert('date' in keys)
                assert('opp_starter_id' in keys)
                assert('opp_pitchers' in keys)
                assert('H' in keys)
                assert('2B' in keys)
                assert('3B' in keys)
                assert('HR' in keys)
                assert('R' in keys)
                assert('AB' in keys)
                assert('BB' in keys)
                assert('HBP' in keys)
                assert('postgame_BA' in keys)
                assert('postgame_OBP' in keys)
                assert('postgame_SLG' in keys)
                assert('postgame_OPS' in keys)
                assert('night_game' in keys)
                assert('temp' in keys)
                assert('opp_starter_righty' in keys)
                assert('opp_starter' in keys)
                assert('opp_starter_id' in keys)
                assert('opp_starter_name' in keys)


# =========================== PITCHING TESTS =========================== #


def test_bullpen_keys():
    """
    Tests that all fields are present in each bullpen game.
    """
    for year in BULLPEN_DATA:
        data = BULLPEN_DATA[year]
        for team in data:
            dates = list(data[team])
            for i in range(len(dates)):
                keys = list(data[team][dates[i]])
                if i > 0:
                    assert('pregame_ERA' in keys)
                    assert('pregame_WHIP' in keys)
                    assert('season_outs' in keys)
                    assert('season_ER' in keys)
                    assert('season_H' in keys)
                    assert('season_BB' in keys)
                assert('game_H' in keys)
                assert('game_ER' in keys)
                assert('game_BB' in keys)
                assert('game_H' in keys)


def test_bullpen_season_stats():
    """
    Test that randomly selected dates from a team's season have been correctly
    added from previous games.
    """
    for year in BULLPEN_DATA:
        data = BULLPEN_DATA[year]
        for team in data:
            dates = list(data[team])
            # choose a random date 10 times, see if stats were calculated correctly
            for i in range(10):
                choice = rand.randint(1, len(dates)-1)
                chosen_date = dates[choice]
                chosen_game = data[team][chosen_date]
                season_outs, season_ER, season_BB, season_H = (0, 0, 0, 0)
                for date in dates[:choice]:
                    game = data[team][date]
                    season_outs += game['game_outs']
                    season_ER += game['game_ER']
                    season_BB += game['game_BB']
                    season_H += game['game_H']
                assert(season_outs == chosen_game['season_outs'])
                assert(season_ER == chosen_game['season_ER'])
                assert(season_BB == chosen_game['season_BB'])
                assert(season_H == chosen_game['season_H'])


def check_bullpen(game, outs, hits, earned_runs, walks):
    """
    Verifty certain values are correct.
    """
    assert(game['game_outs'] == outs)
    assert(game['game_H'] == hits)
    assert(game['game_ER'] == earned_runs)
    assert(game['game_BB'] == walks)


def test_specific_bullpen_games():
    """
    Test that the bullpen stats are correct for the
    selected games. Hard-coded stats calculated by hand to
    be compared with the scraped values.
    """
    game1 = BULLPEN_DATA['2021']['ARI']['2021-04-06']
    game2 = BULLPEN_DATA['2021']['SFG']['2021-07-04']
    game3 = BULLPEN_DATA['2021']['BOS']['2021-08-17 (2)']
    game4 = BULLPEN_DATA['2021']['BAL']['2021-08-14']
    game5 = BULLPEN_DATA['2021']['SEA']['2021-04-23']
    check_bullpen(game1, 22, 5, 2, 4)
    check_bullpen(game2, 1, 0, 0, 1)
    check_bullpen(game3, 3, 1, 0, 0)
    check_bullpen(game4, 14, 8, 9, 2)
    check_bullpen(game5, 10, 5, 0, 0)


def test_ERA_fn():
    """
    Test that calculate_ERA() in utils.py works.
    """
    assert(utils.calculate_ERA(1, 1) == 9)
    assert(utils.calculate_ERA(2, 2.33) == 7.73)
    assert(utils.calculate_ERA(0, 9) == 0)
    assert(utils.calculate_ERA(1, 21) == .43)
    assert(utils.calculate_ERA(23, 40) == 5.17)
    assert(utils.calculate_ERA(258, 974) == 2.38)


def test_WHIP_fn():
    """
    Test that calculate_WHIP() in utils.py works.
    """
    assert(utils.calculate_WHIP(7, 0, 0) == 0)
    assert(utils.calculate_WHIP(1, 1, 0) == 1)
    assert(utils.calculate_WHIP(9, 8, 4) == 1.33)
    assert(utils.calculate_WHIP(21, 1, 0) == .05)
    assert(utils.calculate_WHIP(428, 340, 98) == 1.02)


def test_ERA_stats():
    """
    Test that ERAs were calculated correctly. 
    """
    game1 = BULLPEN_DATA['2021']['CIN']['2021-04-05']
    game2 = BULLPEN_DATA['2021']['BOS']['2021-04-05']
    assert(game1['pregame_ERA'] == 2.63)
    assert(game2['pregame_ERA'] == 4.30)
    # add more for pitcher stats


def test_WHIP_stats():
    """
    Test that WHIPs were calculated correctly.
    """
    game1 = BULLPEN_DATA['2021']['SEA']['2021-04-05']
    game2 = BULLPEN_DATA['2021']['OAK']['2021-04-04']
    assert(game1['pregame_WHIP'] == .91)
    assert(game2['pregame_WHIP'] == 2.11)
    # aadd more for pitcher stats


def test_opp_pitchers():
    """
    Test that there are no duplicate names in the opp_pitchers field.
    """
    for year in GAME_DATA:
        data = GAME_DATA[year]
        for team in data:
            for date in data[team]:
                game = data[team][date]
                names = set()
                assert(len(data[team][date]['opp_pitchers']) > 0)
                for name in game['opp_pitchers']:
                    names.add(name)
                assert(len(names) == len(game['opp_pitchers']))


def test_starters_match():
    """
    Test that the starting pitcher scraped from the hitting game log
    matches the starting pitcher scraped from the pitching game log
    for a certain game.
    """
    for year in GAME_DATA:
        for team in GAME_DATA[year]:
            for date in GAME_DATA[year][team]:
                game = GAME_DATA[year][team][date]
                starter = game['opp_starter']            # B.Snell
                starter_name = game['opp_starter_name']  # Blake Snell
                starter_id = game['opp_starter_id']      # snellbl01
                last_name = starter.split('.')[-1]
                assert(last_name in starter_name)
