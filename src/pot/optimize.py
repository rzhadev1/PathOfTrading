"""
A mixed integer linear optimization for finding currency mispricings in the path of exile currency exchange.

This model borrows heavily from the following resource: 
https://mobook.github.io/MO-book/notebooks/04/05-cryptocurrency-arbitrage.html#pyomo-model-for-arbitrage-with-capacity-constraints
"""

import pyomo.environ as pyo
import pandas as pd
import networkx as nx
import numpy as np

from .exceptions import NonIntegerQuantity
from .monad import PyomoMonad, Solver

def order_book_to_digraph(order_book : pd.DataFrame):
    """ Convert a pandas dataframe representation of the market into a directed graph. """
    graph = nx.MultiDiGraph()

    for order in order_book.index:
        dst = order_book.at[order, "have"]
        src = order_book.at[order, "want"]
        stock = order_book.at[order, "stock"]

        # the *unit* price of want in terms of have (want / have)
        ratio = order_book.at[order, "ratio"]
        gold_cost = order_book.at[order, "gold_cost"]

        # the maximum amount of want we can convert
        capacity = round(stock * ratio)

        # find the minimum increment that this trade can occur at 
        # note that this is because partial orders are allowed
        full_trade_dst = capacity
        full_trade_src = stock

        # make sure that both of these are correctly integers
        # the problem will be infeasible if they arent
        if full_trade_dst == int(full_trade_dst):
            full_trade_dst = int(full_trade_dst)
        else:
            raise NonIntegerQuantity("Order must have an integer quantity of want currency.")
        
        if full_trade_src == int(full_trade_src):
            full_trade_src = int(full_trade_src)
        else:
            raise NonIntegerQuantity("Order must have an integer quantity of have currency.")

        # number of possible partial orders
        increments = np.gcd(full_trade_dst, full_trade_src)

        # the minimum increment of each trade for the source currency
        min_inc_sz_src = full_trade_dst / increments

        graph.add_edge(
            src,
            dst,
            a=1/ratio,
            capacity=capacity,
            gold_cost=gold_cost,
            min_inc_sz=min_inc_sz_src,
            partials=increments
        )

    return graph

def optimal_conversion(order_book_graph : nx.MultiDiGraph, from_portfolio : dict, to_currency : str,
                       timesteps: int, window: int, init_gold : int):
    """ Find the optimal conversion from a from_portfolio of currencies into an ending currency. 
    :param order_book_graph: a directed graph representation of the order book. 
    :param from_portfolio: a dictionary containing (from_currency, from_currency_quantity) pairs. 
    :param to_currency: a string specifying the desired ending currency
    :param timesteps: the number of timesteps allowed
    :param init_gold: the amount of starting gold
    :param window: the number of available spaces in the trading window
    """

    for key in from_portfolio.keys():
        if from_portfolio[key] != int(from_portfolio[key]):
            raise NonIntegerQuantity("Non integer starting portfolio. ")

    m = pyo.ConcreteModel()

    # length of the trading chain
    m.T0 = pyo.RangeSet(0, timesteps)
    m.T1 = pyo.RangeSet(1, timesteps)

    # currency nodes and trading edges
    m.NODES = pyo.Set(initialize=list(order_book_graph.nodes))
    m.EDGES = pyo.Set(initialize=list(order_book_graph.edges))

    # currency on hand at each node
    m.v = pyo.Var(m.NODES, m.T0, domain=pyo.NonNegativeReals)

    # amount traded on each edge at each trade
    m.x = pyo.Var(m.EDGES, m.T1, domain=pyo.NonNegativeReals)

    # boolean indicating if a trade was made
    m.b = pyo.Var(m.EDGES, m.T1, domain=pyo.Binary)

    # the number of partial orders on each trade
    m.p = pyo.Var(m.EDGES, m.T1, domain=pyo.NonNegativeIntegers)

    # auxiliary so that we can linearize b * p
    m.lin_bp = pyo.Var(m.EDGES, m.T1, domain=pyo.NonNegativeIntegers)

    # total amount traded on each edge over all trades
    m.z = pyo.Var(m.EDGES, domain=pyo.NonNegativeReals)

    # gold at each time step
    m.g = pyo.Var(m.T0, domain=pyo.NonNegativeReals)

    # the conversion ratio from src -> dst
    @m.Param(m.EDGES)
    def a(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["a"]

    # the # of src that is convertable to dst on this trade 
    @m.Param(m.EDGES)
    def c(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["capacity"]

    # the minimum increment size of a partial order for src -> dst conversion
    @m.Param(m.EDGES)
    def min_inc_sz(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["min_inc_sz"]
    
    # the number of partial orders for a src -> dst conversion
    @m.Param(m.EDGES)
    def partials(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["partials"]
    
    @m.Param(m.EDGES)
    def gold_cost(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["gold_cost"]

    @m.Objective(sense=pyo.maximize)
    def wealth(m):
        return m.v[to_currency, timesteps]
    
    # the following 4 constraints linearize b * p using the aux. variable lin_bp
    @m.Constraint(m.EDGES, m.T1)
    def upper_bd_prod(m, src, dst, idx, t):
        return m.lin_bp[src, dst, idx, t] <= m.b[src, dst, idx, t] * m.partials[src, dst, idx]
    
    @m.Constraint(m.EDGES, m.T1)
    def lower_bd_prod(m, src, dst, idx, t):
        return m.lin_bp[src, dst, idx, t] >= m.p[src, dst, idx, t] - (1 - m.b[src, dst, idx, t]) * m.partials[src, dst, idx]
    
    @m.Constraint(m.EDGES, m.T1)
    def lin_bp_lower(m, src, dst, idx, t):
        return m.lin_bp[src, dst, idx, t] >= 0 

    @m.Constraint(m.EDGES, m.T1)
    def lin_bp_upper(m, src, dst, idx, t):
        return m.lin_bp[src, dst, idx, t] <= m.p[src, dst, idx, t] 

    # trades must occur in multiples of partial orders
    @m.Constraint(m.EDGES, m.T1)
    def integral_trades(m, src, dst, idx, t):
        return m.x[src, dst, idx, t] == m.lin_bp[src, dst, idx, t] * m.min_inc_sz[src, dst, idx]
    
    # we cannot over trade a given order
    @m.Constraint(m.EDGES)
    def total_traded(m, src, dst, idx):
        return m.z[src, dst, idx] == sum([m.x[src, dst, idx, t] for t in m.T1])

    @m.Constraint(m.EDGES)
    def edge_capacity(m, src, dst, idx):
        return m.z[src, dst, idx] <= m.c[src, dst, idx]

    # initial conditions
    @m.Constraint(m.NODES)
    def initial(m, node):
        if node in from_portfolio.keys():
            return m.v[node, 0] == from_portfolio[node]
        return m.v[node, 0] == 0

    @m.Constraint()
    def initial_gold(m):
        return m.g[0] == init_gold

    # positions must stay nonnegative
    @m.Constraint(m.NODES, m.T1)
    def no_shorting(m, node, t):
        out_nodes = [(dst, idx) for src, dst, idx in m.EDGES if src == node]
        return m.v[node, t - 1] >= sum(m.x[node, dst, idx, t] for dst, idx in out_nodes)

    @m.Constraint(m.NODES, m.T1)
    def balances(m, node, t):
        in_nodes = [(src, idx) for src, dst, idx in m.EDGES if dst == node]
        out_nodes = [(dst, idx) for src, dst, idx in m.EDGES if src == node]
        incoming = sum(
            m.x[src, node, idx, t] * m.a[src, node, idx] for src, idx, in in_nodes
        )
        outgoing = sum(m.x[node, dst, idx, t] for dst, idx in out_nodes) 
        return m.v[node, t] == m.v[node, t - 1] + incoming - outgoing
    
    @m.Constraint(m.T1)
    def gold_balances(m, t):
        out_gold = sum(
            m.p[src, dst, idx, t] * m.gold_cost[src, dst, idx] for src, dst, idx, in m.EDGES
        )
        return m.g[t] == m.g[t - 1] - out_gold
    
    # cannot have more than window size number of trades at the same time step
    @m.Constraint(m.T1)
    def window_size(m, t):
        num_trades = sum(m.b[src, dst, idx, t] for src, dst, idx in m.EDGES)
        return num_trades <= window
    
    # return both the optimal amount of wealth we can get, and the 
    # series of trades made
    def report(m):
        trades = []
        for t in m.T1:
            for src, dst, idx in m.EDGES:
                a = m.a[src, dst, idx]
                if m.x[src, dst, idx, t]() > 1e-6:
                    have_qty = m.x[src, dst, idx, t]()
                    want_qty = have_qty * a
                    trades.append({'timestep': t, 'have': src, 'want': dst, 'have_qty' : have_qty, 'want_qty' : want_qty}) 

        return m.wealth(), pd.DataFrame(trades)

    return PyomoMonad(m, effect=report)