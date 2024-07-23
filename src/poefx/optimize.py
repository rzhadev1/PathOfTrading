import pyomo.environ as pyo
import pandas as pd
import sys

solver = 'glpk'
SOLVER = pyo.SolverFactory(solver)
assert SOLVER.available(), f"Solver {solver} is not available."

def optimal_conversion(market_df : pd.DataFrame, from_currency : str, to_currency : str, 
                       from_currency_qty : int, num_trades : int, start_gold : int):
    
    conversions = market_df.set_index(['currency_a', 'currency_b']).to_dict(orient='index')
    rates_dict = {conversion : d['rate'] for conversion, d in conversions.items()}
    inc_dict = {conversion : d['increment_a'] for conversion, d in conversions.items()}
    gold_dict = {conversion : d['gold_cost'] for conversion, d in conversions.items()}

    model = pyo.ConcreteModel()

    # currency nodes 
    model.TO_CURRENCIES = pyo.Set(initialize=market_df['currency_b'].unique())
    model.FROM_CURRENCIES = pyo.Set(initialize=market_df['currency_a'].unique())
    model.CURRENCIES = model.TO_CURRENCIES | model.FROM_CURRENCIES
    # paths between currency nodes
    model.CONVERSIONS = pyo.Set(initialize=model.FROM_CURRENCIES * model.TO_CURRENCIES, filter=lambda _,i,j: i != j) 
    # number of time steps
    model.K = pyo.RangeSet(1, num_trades)

    # the number of currency_a involved in each transaction
    model.INC = pyo.Param(model.CONVERSIONS, initialize=inc_dict)
    # the rate at which we can convert 1 unit of currency_a to currency_b
    model.R = pyo.Param(model.CONVERSIONS, initialize=rates_dict)
    # the cost in gold of making a conversion
    model.GOLD_COST = pyo.Param(model.CONVERSIONS, initialize=gold_dict)

    # the number of transactions made of size INC for a conversion at time step k
    model.T = pyo.Var(model.CONVERSIONS * model.K, domain=pyo.NonNegativeIntegers)
    # the amount of currency i at time step k
    model.X = pyo.Var(model.CURRENCIES * model.K)
    # the amount of currency i that will be converted to currency j at time step k
    model.C = pyo.Var(model.CONVERSIONS * model.K)
    # the amount of gold at time step k
    model.G = pyo.Var(model.K, initialize=start_gold, domain=pyo.NonNegativeIntegers)

    # we maximize the amount of the ending currency
    @model.Objective(sense=pyo.maximize)
    def end_to_currency(model):
        return model.X[to_currency, num_trades]

    # initially, we have B units of the from currency
    @model.Constraint(model.CURRENCIES)
    def initial_conditions(model, currency):
        if currency == from_currency:
            return model.X[currency, 1] == from_currency_qty
        return model.X[currency, 1] == 0

    # enforce that we trade in the given increments
    @model.Constraint(model.CONVERSIONS, model.K)
    def increment_per_trade(model, from_c, to_c, k):
        conv = (from_c, to_c)
        return model.C[conv, k] == model.T[conv, k] * model.INC[conv]

    # can only make a trade if we have sufficient currency
    @model.Constraint(model.CONVERSIONS, model.K)
    def sufficient_currency(model, from_c, to_c, k):
        return model.C[(from_c, to_c), k] <= model.X[from_c, k]
    
    # can only make a trade if we have sufficient gold
    @model.Constraint(model.K)
    def sufficient_gold(model, k):
        return sum([model.T[conv, k] * model.GOLD_COST[conv] for conv in model.CONVERSIONS]) <= model.G[k]
    
    # converting from currency means we lose that currency in the next time step
    @model.Constraint(model.CONVERSIONS, model.K)
    def currency_change_reduction(model, from_c, to_c, k):
        # this constraint is not defined for the last time step
        if k+1 in model.K:
            reduce_total = sum([model.C[(from_c, j), k] for j in model.TO_CURRENCIES if from_c != j])
            return model.X[from_c, k+1] == model.X[from_c, k] - reduce_total
        return pyo.Constraint.Skip
    
    # converting currency means we gain to currency in the next time step
    @model.Constraint(model.CONVERSIONS, model.K)
    def currency_change_gain(model, from_c, to_c, k):
        if k+1 in model.K:
            gain_total = sum([model.C[(i, to_c), k] * model.R[i, to_c] for i in model.FROM_CURRENCIES if to_c != i])
            return model.X[to_c, k+1] == model.X[to_c, k] + gain_total
        return pyo.Constraint.Skip

    # incur fixed cost in gold for making a trade    
    @model.Constraint(model.K)
    def gold_reduction(model, k):
        if k+1 in model.K:
            reduce_total = sum([model.T[conv, k] * model.GOLD_COST[conv] for conv in model.CONVERSIONS])
            return model.G[k+1] == model.G[k] - reduce_total
        return pyo.Constraint.Skip

    model.pprint()
    result = SOLVER.solve(model, tee=True)
    print(model.X[to_currency, num_trades]())

if __name__ == '__main__':
    df = pd.read_csv('currency_market1.csv')
    optimal_conversion(df, 'Chaos Orb', 'Divine Orb', 100, 3, 1000000)