import argparse
import pandas as pd
import sys
sys.path.append('src')

from pot.monad import Solver
from pot.optimize import order_book_to_digraph, optimal_conversion

parser = argparse.ArgumentParser(description='Process currency market order book.')
parser.add_argument('--orderbook', '-f', type=str, required=True, dest='order_book', action='store',
                    help='path to .csv file representing the currency market order book.')

parser.add_argument('--havecurrency', '-have', type=str, default='Chaos Orb', dest='have_curr', action='store',
                    help='string name of currency that is converted from.')

parser.add_argument('--havecurrencyqty', '-hqty', type=int, default=100, dest='have_curr_qty', action='store',
                    help='amount of have currency to start with.')

parser.add_argument('--wantcurrency', '-want', type=str, default='Divine Orb', dest='want_curr', action='store',
                    help='string name of currency that is converted to.')

parser.add_argument('--numtrades', '-t', type=int, default=10, dest='num_trades',action='store', 
                    help='number of trades that can be made.')

parser.add_argument('--startgold', '-g', type=int, default=1000000, dest='start_gold', action='store',
                    help='starting amount of gold.')

parser.add_argument('--solver', '-s', type=str, default='appsi_highs', dest='solver', action='store',
                    help='solver used by pyomo.')

args = parser.parse_args()
df = pd.read_csv(args.order_book)
market_graph = order_book_to_digraph(df)
sol = (optimal_conversion(
    market_graph, 
    args.have_curr, 
    args.want_curr, 
    args.have_curr_qty, 
    args.num_trades, 
    args.start_gold
) >> Solver(args.solver))

if sol is None:
    print('Error constructing model.')
    print(sol.status)

else:
    opt, trades = sol()
    print(f'Optimal # of {args.want_curr}: {opt}')
    print(trades)
