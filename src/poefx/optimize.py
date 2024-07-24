import pyomo.environ as pyo
import pandas as pd
from monad import PyomoMonad, Solver

def optimal_conversion(market_df : pd.DataFrame, from_currency : str, to_currency : str, 
                       from_currency_qty : int, num_trades : int, start_gold : int):
    
    m = pyo.ConcreteModel()
    m.TRADES = pyo.RangeSet(0, num_trades)
    m.TRANSACTIONS = pyo.RangeSet(1, num_trades)

    # set of currencies that we can start a transaction with
    m.FROM_CURR = pyo.Set(initialize=market_df['currency_a'].unique())

    # set of currencies that we can get from a transaction
    m.TO_CURR = pyo.Set(initialize=market_df['currency_b'].unique())

    # set of all currencies
    m.CURR = m.FROM_CURR | m.TO_CURR

    # set of possible conversions between a currency pair
    conversions = market_df.set_index(['currency_a', 'currency_b']).to_dict(orient='index')
    m.CONV = pyo.Set(initialize=conversions.keys())

    # the rate at which we can convert currency a -> currency b
    rates_dict = {conversion : d['qty_b'] / d['qty_a'] for conversion, d in conversions.items()}
    m.RATES = pyo.Param(m.CONV, initialize=rates_dict)

    # the minimum increment at which we can convert currency a -> currency b
    min_inc_dict = {conversion : 1 / rate for conversion, rate in rates_dict.items()}
    m.MIN_INC = pyo.Param(m.CONV, initialize=min_inc_dict)

    # the gold cost associated with each transaction
    gold_dict = {conversion : d['gold_cost'] for conversion, d in conversions.items()}
    m.GOLD_COST = pyo.Param(m.CONV, initialize=gold_dict)

    # the amount of gold on hand at a given trade t
    m.g = pyo.Var(m.TRADES, domain=pyo.NonNegativeReals)

    # the amount of currency i on hand after trade t
    m.x = pyo.Var(m.CURR, m.TRADES, domain=pyo.NonNegativeReals)

    # the amount of currency i committed to be converted to currency j in transaction t
    m.c = pyo.Var(m.CONV, m.TRANSACTIONS, domain=pyo.NonNegativeReals)

    # the number of increments made for a conversion, which must be integer
    m.incs = pyo.Var(m.CONV, m.TRANSACTIONS, domain=pyo.NonNegativeIntegers)

    # start with initial number of the starting currency
    @m.Constraint(m.CURR)
    def initial_cond(m, i):
        if i == from_currency:
            return m.x[i, 0] == from_currency_qty
        return m.x[i, 0] == 0
    
    # start with initial amount of gold
    @m.Constraint()
    def initial_gold(m):
        return m.g[0] == start_gold
    
    # must trade in the correct increments
    @m.Constraint(m.CONV, m.TRANSACTIONS)
    def trade_increments(m, i, j, t):
        return m.c[i,j,t] == m.incs[i,j,t] * m.MIN_INC[i,j]
    
    # gold balance is maintained after a round of transactions
    @m.Constraint(m.TRANSACTIONS)
    def gold_balance(m, t):
        # the gold cost incurred from the transactions made
        cost = sum(m.incs[i,j,t] * m.GOLD_COST[i,j] for (i,j) in m.CONV)
        return m.g[t] == m.g[t-1] - cost
    
    # balances are maintained after a round of transactions
    @m.Constraint(m.CURR, m.TRANSACTIONS)
    def balance(m, j, t):
        outgoing = sum(m.c[j, i, t] for i in m.CURR if i != j and (j,i) in m.CONV)
        incoming = sum(m.RATES[(i, j)] * m.c[(i, j), t] for i in m.CURR if i != j and (i,j) in m.CONV)
        return m.x[j, t] == m.x[j, t-1] - outgoing + incoming
    
    @m.Constraint(m.CURR, m.TRANSACTIONS)
    def no_shorting(m, j, t):
        return m.x[j, t-1] >= sum(m.c[j, i, t] for i in m.CURR if i != j and (j,i) in m.CONV)
    
    # maximize the ending currency
    @m.Objective(sense=pyo.maximize)
    def conversion_amt(m):
        return m.x[to_currency, num_trades]
    
    # result call back
    def result(m):
        trades = {(curr_a, curr_b, step): m.c[curr_a, curr_b, step].value for curr_a,curr_b,step in m.c}
        return m.conversion_amt(), trades

    return PyomoMonad(m, effect=result)

if __name__ == '__main__':
    df = pd.read_csv('currency_market1.csv')
    amt, trades = (optimal_conversion(df, 'Chaos Orb', 'Divine Orb', 121, 3, 1000000) >> Solver('cbc'))()
    print(trades)
    print(amt)