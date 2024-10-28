def calculate_margin(odds):
    """
    Calculates the bookmaker's margin (overround) from the given decimal odds.

    Args:
        odds (list): A list of decimal odds (e.g., [odds1, odds2])

    Returns:
        float: Calculated margin
    """
    implied_probs = [1 / odd for odd in odds]
    margin = sum(implied_probs) - 1
    return margin


def kelly_bet(prob_win, b, bankroll, kelly_multiplier=1.0):
    """
    Calculate the Kelly bet size.

    Args:
        prob_win (float): Probability of winning (e.g., 0.55 for a 55% chance).
        b (float): The proportion of the bet gained with a win (e.g., 2.0 for 2:1 odds).
        bankroll (float): Current bankroll size in dollars.
        kelly_multiplier (float): Multiplier to adjust the Kelly bet size for more conservative bets (default is 1.0).

    Returns:
        float: Amount of money to bet according to the Kelly criterion.
    """
    # Calculate the Kelly fraction
    kelly_fraction = prob_win - (1 - prob_win) / b

    # Adjust with the Kelly multiplier
    adjusted_fraction = kelly_fraction * kelly_multiplier

    # Calculate the amount to bet
    bet_size = bankroll * adjusted_fraction

    return bet_size
