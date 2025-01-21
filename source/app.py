import os
import statistics

from flask import Flask, request, render_template, make_response
import numpy as np
import pybettor
import shin

from implied_odds import implied_odds
from utils import calculate_margin, kelly_bet

app = Flask(__name__, template_folder='../templates')


@app.route("/", methods=["GET", "POST"])
def index():
    # Initialize default values for result variables
    # Retrieve Kelly values from cookies if they exist
    kelly_budget_input = request.cookies.get("kelly_budget", "")
    kelly_mult_input = request.cookies.get("kelly_mult", "")
    odds_input = ""
    final_odds = ""
    error = None

    multiplicative_results_str = None
    additive_results_str = None
    power_results_str = None
    shin_results_str = None
    min_results_str = None
    avg_results_str = None
    error = None

    if request.method == "POST":
        # Get inputs
        kelly_budget_input = request.form.get("kelly_budget", "")
        kelly_mult_input = request.form.get("kelly_mult", "")
        odds_input = request.form.get("odds_input", "")
        final_odds_input = request.form.get("final_odds", "")

        # Validate input and perform calculations
        try:
            # Validate input
            if not kelly_budget_input or not kelly_mult_input or not odds_input or not final_odds_input:
                raise ValueError("All fields are required.")
            kelly_budget = float(kelly_budget_input)
            kelly_mult = float(kelly_mult_input)
            final_odds = float(final_odds_input)

            # Parse odds input
            legs = odds_input.split(',')
            legs_odds = []
            legs_probs = []
            for leg in legs:
                odds = list(map(float, leg.split('/')))
                probs = [1 / o for o in odds]
                legs_odds.append(odds)
                legs_probs.append(probs)

            # Calculate raw margin for each leg
            margins = [calculate_margin(odds) for odds in legs_odds]

            # Calculations for each method
            results = {
                "mult": calculate_multiplicative_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult),
                "add": calculate_additive_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult),
                "power": calculate_power_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult),
                "shin": calculate_shin_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult)
            }

            evs = [result[1][1] for result in results.items()]
            kellys = [result[1][2] for result in results.items()]

            ev_avg = round(statistics.mean(evs), 2)
            kelly_avg = round(statistics.mean(kellys), 2)
            avg_results_str = f"AVG: EV% = {ev_avg}%, Kelly Wager = ${kelly_avg}"

            ev_min = min(evs)
            kelly_min = min(kellys)
            min_results_str = f"MIN: EV% = {ev_min}%, Kelly Wager = ${kelly_min}"

            multiplicative_results_str = results["mult"][0]
            additive_results_str = results["add"][0]
            power_results_str = results["power"][0]
            shin_results_str = results["shin"][0]

        except Exception as e:
            error = f"Invalid input. Please enter valid numbers.\n\nError: '{str(e)}'"

        response = make_response(render_template(
            "index.html",
            multiplicative_results=multiplicative_results_str,
            additive_results=additive_results_str,
            power_results=power_results_str,
            shin_results=shin_results_str,
            min_results=min_results_str,
            avg_results=avg_results_str,
            kelly_budget=kelly_budget_input,
            kelly_mult=kelly_mult_input,
            odds_input=odds_input,
            final_odds=final_odds_input,
            error=error
        ))

        # Save Kelly values to cookies, with 1 year expiration
        response.set_cookie("kelly_budget", kelly_budget_input, max_age=60 * 60 * 24 * 365)
        response.set_cookie("kelly_mult", kelly_mult_input, max_age=60 * 60 * 24 * 365)

        # Render page with calculated values
        return response

    # Request is not POST: render page, fill form with values from cookies
    return render_template("index.html",
                           kelly_budget=kelly_budget_input,
                           kelly_mult=kelly_mult_input)


def calculate_power_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    # Devig each leg
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

    return (
        f"{summary}<br>EV% = {total_ev}%, Kelly Wager = ${total_kelly_bet}",
        total_ev,
        total_kelly_bet
    )


def calculate_additive_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    # Devig each leg
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

    return (
        f"{summary}<br>EV% = {total_ev}%, Kelly Wager = ${total_kelly_bet}",
        total_ev,
        total_kelly_bet
    )


def calculate_multiplicative_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    # Devig each leg
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

    return (
        f"{summary}<br>EV% = {total_ev}%, Kelly Wager = ${total_kelly_bet}",
        total_ev,
        total_kelly_bet
    )


def calculate_shin_method(legs_odds, legs_probs, margins, final_odds, kelly_budget, kelly_mult):
    # Devig each leg
    legs_odds_devigged = []
    legs_odds_devigged_us = []
    for i in range(len(legs_odds)):
        devigged_probs = shin.calculate_implied_probabilities(legs_odds[i])
        devigged_odds = [1/p for p in devigged_probs]
        devigged_odds_us = pybettor.convert_odds(devigged_probs, cat_in="prob", cat_out="us")
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

    return (
        f"{summary}<br>EV% = {total_ev}%, Kelly Wager = ${total_kelly_bet}",
        total_ev,
        total_kelly_bet
    )


if __name__ == "__main__":
    # # Run in localhost
    # app.run(debug=True)

    # Run in hosting
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
