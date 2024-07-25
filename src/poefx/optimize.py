"""
The model borrows heavily from the following resource: 
https://mobook.github.io/MO-book/notebooks/04/05-cryptocurrency-arbitrage.html#pyomo-model-for-arbitrage-with-capacity-constraints
"""

import pyomo.environ as pyo
import pandas as pd
import networkx as nx
import numpy as np
import math
from monad import PyomoMonad, Solver

def order_book_to_digraph(order_book : pd.DataFrame):
    graph = nx.MultiDiGraph()

    for order in order_book.index:
        src = order_book.at[order, "have"]
        dst = order_book.at[order, "want"]
        stock = order_book.at[order, "stock"]

        # the *unit* price in terms of want: have (1)
        ratio = order_book.at[order, "ratio"]
        gold_cost = order_book.at[order, "gold_cost"]

        # the maximum amount we can convert
        capacity = stock / ratio

        # find the minimum increment that this trade can occur at 
        # note that this is because partial orders are allowed
        full_trade_dst = int(ratio * stock)
        full_trade_src = int(stock)
        
        # number of possible partial orders
        increments = math.gcd(full_trade_dst, full_trade_src)
        # the minimum increment of each trade for the source currency
        min_inc_src = full_trade_src / increments

        graph.add_edge(
            src,
            dst,
            a=ratio,
            capacity=capacity,
            gold_cost=gold_cost,
            min_inc=min_inc_src
        )

    return graph

def optimal_conversion(order_book_graph : nx.MultiDiGraph, from_currency : str, to_currency : str, 
                       from_currency_qty : int, num_trades: int, init_gold : int):
    
    m = pyo.ConcreteModel()

    # length of the trading chain
    m.T0 = pyo.RangeSet(0, num_trades)
    m.T1 = pyo.RangeSet(1, num_trades)

    # currency nodes and trading edges
    m.NODES = pyo.Set(initialize=list(order_book_graph.nodes))
    m.EDGES = pyo.Set(initialize=list(order_book_graph.edges))

    # currency on hand at each node
    m.v = pyo.Var(m.NODES, m.T0, domain=pyo.NonNegativeReals)

    # amount traded on each edge at each trade
    m.x = pyo.Var(m.EDGES, m.T1, domain=pyo.NonNegativeReals)

    # the number of partial orders on each trade
    m.p = pyo.Var(m.EDGES, m.T1, domain=pyo.NonNegativeIntegers)

    # total amount traded on each edge over all trades
    m.z = pyo.Var(m.EDGES, domain=pyo.NonNegativeReals)

    # gold at each time step
    m.g = pyo.Var(m.T0, domain=pyo.NonNegativeReals)

    # "multiplier" on each trading edge
    @m.Param(m.EDGES)
    def a(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["a"]

    @m.Param(m.EDGES)
    def c(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["capacity"]

    @m.Param(m.EDGES)
    def min_inc(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["min_inc"]
    
    @m.Param(m.EDGES)
    def gold_cost(m, src, dst, idx):
        return order_book_graph.edges[(src, dst, idx)]["gold_cost"]

    @m.Objective(sense=pyo.maximize)
    def wealth(m):
        return m.v[to_currency, num_trades]
    
    @m.Constraint(m.EDGES, m.T1)
    def integral_trades(m, src, dst, idx, t):
        return m.x[src, dst, idx, t] == m.p[src, dst, idx, t] * m.min_inc[src, dst, idx]
    
    @m.Constraint(m.EDGES)
    def total_traded(m, src, dst, idx):
        return m.z[src, dst, idx] == sum([m.x[src, dst, idx, t] for t in m.T1])

    @m.Constraint(m.EDGES)
    def edge_capacity(m, src, dst, idx):
        return m.z[src, dst, idx] <= m.c[src, dst, idx]

    @m.Constraint(m.NODES)
    def initial(m, node):
        if node == from_currency:
            return m.v[node, 0] == from_currency_qty
        return m.v[node, 0] == 0

    @m.Constraint()
    def initial_gold(m):
        return m.g[0] == init_gold

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

    # return both the optimal amount of wealth we can get, and the 
    # series of trades we should make
    def report(m):
        return m.wealth()

    return PyomoMonad(m, effect=report)

if __name__ == '__main__':
    df = pd.read_csv('currency_market.csv')
    dg = order_book_to_digraph(df)
    wealth = (optimal_conversion(dg, 'Chaos Orb', 'Divine Orb', 200, 10, 100000) >> Solver('appsi_highs'))()
    print(wealth)