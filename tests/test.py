import pandas as pd
import sys
sys.path.append('../src')
from pot.monad import Solver
from pot.optimize import order_book_to_digraph, optimal_conversion

if __name__ == '__main__':
    df = pd.read_csv('currency_market.csv')
    dg = order_book_to_digraph(df)
    monad = optimal_conversion(dg, 'Chaos Orb', 'Divine Orb', 100, 10, 100000) >> Solver('appsi_highs')
    if monad is not None:
        wealth, trades = monad()
        print(wealth)
        print(trades)
    else:
        print(monad.status)