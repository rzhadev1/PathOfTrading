import pandas as pd
import sys
sys.path.append('../src')
from pot.monad import Solver
from pot.optimize import order_book_to_digraph, optimal_conversion

if __name__ == '__main__':
    df = pd.read_csv('currency_market.csv')
    dg = order_book_to_digraph(df)
    from_portfolio = {
        'Chaos Orb': 100,
        'Exalted Orb' : 50,
    }
    monad = optimal_conversion(dg, from_portfolio, 'Divine Orb', 3, 5, 100000) >> Solver('appsi_highs')

    if monad is not None:
        wealth, trades = monad()
        print(wealth)
        print(trades)
    else:
        print(monad.status)