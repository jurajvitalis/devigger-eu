import os
from flask import Flask, request, render_template
import numpy as np
import pybettor

from implied_odds import implied_odds
from utils import calculate_margin, kelly_bet

app = Flask(__name__, template_folder='../templates')


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            # Get form values
            kelly_budget = float(request.form.get("kelly_budget"))
            kelly_mult = float(request.form.get("kelly_mult"))
            odds_input = request.form.get("odds_input")
            final_odds = float(request.form.get("final_odds"))

            # Parse input
            legs = odds_input.split(',')
            legs_odds = []
            legs_probs = []
            for leg in legs:
                odds = list(map(float, leg.split('/')))
                probs = [1 / o for o in odds]
                legs_odds.append(odds)
                legs_probs.append(probs)

            margins = [calculate_margin(odds) for odds in legs_odds]

            # Calculations for each method
            multiplicative_results = calculate_multiplicative_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult)
            additive_results = calculate_additive_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult)
            power_results = calculate_power_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult)

            # Pass results to the template
            return render_template(
                "index.html",
                multiplicative_results=multiplicative_results,
                additive_results=additive_results,
                power_results=power_results,
                kelly_budget=kelly_budget,
                kelly_mult=kelly_mult,
                odds_input=odds_input,
                final_odds=final_odds
            )

        except ValueError:
            return render_template("index.html", error="Invalid input. Please enter valid numbers.")

    return render_template("index.html", result=None)


def calculate_power_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    legs_odds_devigged = []
    legs_odds_devigged_us = []
    for i in range(len(legs_odds)):
        devigged_odds = implied_odds(legs_probs[i], category="dec", method="power", normalize=False,
                                     margin=margins[i])['implied_odds']
        devigged_odds_us = pybettor.convert_odds(devigged_odds, cat_in="dec", cat_out="us")
        legs_odds_devigged.append(devigged_odds)
        legs_odds_devigged_us.append(devigged_odds_us)

    # Total odds calculation
    total_odds_devigged = np.prod([leg_odds[0] for leg_odds in legs_odds_devigged])
    total_odds_devigged_us = pybettor.convert_odds(total_odds_devigged, cat_in="dec", cat_out="us")

    # EV calculation
    total_ev = round(pybettor.expected_value_calc(1 / total_odds_devigged, final_odds, category="dec", risk=100), 2)

    # Kelly bet amount calculation
    if kelly_mult and kelly_budget:
        total_kelly_bet = round(kelly_bet(1 / total_odds_devigged, final_odds - 1, kelly_budget, kelly_mult), 2)

    # Output formatting
    legs_summary = []
    for i in range(len(legs_odds_devigged)):
        legs_summary.append(f"Leg#{i} ({legs_odds[i][0]}): Margin = {round(margins[i] * 100, 2)}% | "
                            f"Fair Value = {round(legs_odds_devigged[i][0], 2)} "
                            f"(US {legs_odds_devigged_us[i][0]}) "
                            f"({round(1 / legs_odds_devigged[i][0] * 100, 2)}%)")
    summary = "<br>".join(legs_summary)

    summary += f"<br>Final Odds ({final_odds}): Total Fair Value = {round(total_odds_devigged, 2)} " \
               f"(US {total_odds_devigged_us[0]}) ({round(1 / total_odds_devigged * 100, 2)}%)"

    return f"{summary}<br>EV% = {round(total_ev, 2)}%, Kelly Wager = ${total_kelly_bet}"


def calculate_additive_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    legs_odds_devigged = []
    legs_odds_devigged_us = []
    for i in range(len(legs_odds)):
        devigged_odds = implied_odds(legs_probs[i], category="dec", method="additive", normalize=False,
                                     margin=margins[i])
        devigged_odds_us = pybettor.convert_odds(devigged_odds, cat_in="dec", cat_out="us")
        legs_odds_devigged.append(devigged_odds)
        legs_odds_devigged_us.append(devigged_odds_us)

    # Total odds calculation
    total_odds_devigged = np.prod([leg_odds[0] for leg_odds in legs_odds_devigged])
    total_odds_devigged_us = pybettor.convert_odds(total_odds_devigged, cat_in="dec", cat_out="us")

    # EV calculation
    total_ev = round(pybettor.expected_value_calc(1 / total_odds_devigged, final_odds, category="dec", risk=100), 2)

    # Kelly bet amount calculation
    if kelly_mult and kelly_budget:
        total_kelly_bet = round(kelly_bet(1 / total_odds_devigged, final_odds - 1, kelly_budget, kelly_mult), 2)

    # Output formatting
    legs_summary = []
    for i in range(len(legs_odds_devigged)):
        legs_summary.append(f"Leg#{i} ({legs_odds[i][0]}): Margin = {round(margins[i] * 100, 2)}% | "
                            f"Fair Value = {round(legs_odds_devigged[i][0], 2)} "
                            f"(US {legs_odds_devigged_us[i][0]}) "
                            f"({round(1 / legs_odds_devigged[i][0] * 100, 2)}%)")
    summary = "<br>".join(legs_summary)

    summary += f"<br>Final Odds ({final_odds}): Total Fair Value = {round(total_odds_devigged, 2)} " \
               f"(US {total_odds_devigged_us[0]}) ({round(1 / total_odds_devigged * 100, 2)}%)"

    return f"{summary}<br>EV% = {round(total_ev, 2)}%, Kelly Wager = ${total_kelly_bet}"


def calculate_multiplicative_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    legs_odds_devigged = []
    legs_odds_devigged_us = []
    for i in range(len(legs_odds)):
        devigged_odds = implied_odds(legs_probs[i], category="dec", method="basic", normalize=False,
                                     margin=margins[i])
        devigged_odds_us = pybettor.convert_odds(devigged_odds, cat_in="dec", cat_out="us")
        legs_odds_devigged.append(devigged_odds)
        legs_odds_devigged_us.append(devigged_odds_us)

    # Total odds calculation
    total_odds_devigged = np.prod([leg_odds[0] for leg_odds in legs_odds_devigged])
    total_odds_devigged_us = pybettor.convert_odds(total_odds_devigged, cat_in="dec", cat_out="us")

    # EV calculation
    total_ev = round(pybettor.expected_value_calc(1 / total_odds_devigged, final_odds, category="dec", risk=100), 2)

    # Kelly bet amount calculation
    if kelly_mult and kelly_budget:
        total_kelly_bet = round(kelly_bet(1 / total_odds_devigged, final_odds - 1, kelly_budget, kelly_mult), 2)

    # Output formatting
    legs_summary = []
    for i in range(len(legs_odds_devigged)):
        legs_summary.append(f"Leg#{i} ({legs_odds[i][0]}): Margin = {round(margins[i] * 100, 2)}% | "
                            f"Fair Value = {round(legs_odds_devigged[i][0], 2)} "
                            f"(US {legs_odds_devigged_us[i][0]}) "
                            f"({round(1 / legs_odds_devigged[i][0] * 100, 2)}%)")
    summary = "<br>".join(legs_summary)

    summary += f"<br>Final Odds ({final_odds}): Total Fair Value = {round(total_odds_devigged, 2)} " \
               f"(US {total_odds_devigged_us[0]}) ({round(1 / total_odds_devigged * 100, 2)}%)"

    return f"{summary}<br>EV% = {round(total_ev, 2)}%, Kelly Wager = ${total_kelly_bet}"


if __name__ == "__main__":
    # Run in localhost
    # app.run(debug=True)

    # Run in hosting
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
