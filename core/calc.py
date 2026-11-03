"""Profit maths. Fees = price * fee_pct/100 + fixed_fee."""


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def calculate_profit(sourcing, price, shipping=0, fee_pct=0, fixed_fee=0,
                     packaging=0, advertising=0, other=0, target_margin_pct=25.0):
    sourcing, price, shipping = _f(sourcing), _f(price), _f(shipping)
    fee_pct, fixed_fee, packaging = _f(fee_pct), _f(fixed_fee), _f(packaging)
    advertising, other, tm = _f(advertising), _f(other), _f(target_margin_pct) / 100
    fees = price * fee_pct / 100 + fixed_fee
    landed = sourcing + shipping + packaging
    total_cost = landed + fees + advertising + other
    gross_profit = price - landed                 # before fees, ads and other
    net_profit = price - total_cost
    margin = net_profit / price * 100 if price > 0 else 0.0
    roi = net_profit / total_cost * 100 if total_cost > 0 else 0.0
    fixed_costs = landed + fixed_fee + advertising + other
    denom = 1 - fee_pct / 100
    break_even = fixed_costs / denom if denom > 0 else float("inf")
    max_sourcing = price * (1 - tm - fee_pct / 100) - fixed_fee - shipping - packaging - advertising - other
    return {
        "fees": fees, "total_cost": total_cost, "gross_profit": gross_profit,
        "net_profit": net_profit, "margin_pct": margin, "roi_pct": roi,
        "break_even_price": break_even, "max_sourcing_cost": max(max_sourcing, 0.0),
        "target_margin_pct": tm * 100,
    }
