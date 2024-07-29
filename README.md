# Path of Trading (PoT)
PoE currency markets 

## Use cases
- Arbitraging cross currency exchange rates: finding a sequence of trades that starts and ends at the same currency resulting in a net increase in wealth. 

- Optimal currency conversion: finding a sequence of trades that optimally converts a given amount of starting currency into a desired currency.

The arbitrage problem is a special case of the currency conversion problem, with start currency = ending currency. 
## Inputs
The model assumes input in the form of a .csv file which represents the entire order book of the currency market. Each order specifies a starting currency (called have), an ending currency (called want), a specified ratio of $\frac{want}{have}$ that prices the have currency in terms of want currency, *stock* representing the quantity of the have currency, and a gold cost per each transaction. 

See the example section for a sample input. 

## Model
The currency exchange is similar to real life forex/cryptocurrency markets. A few main differences (besides the input format) exist: 
- The currency exchange requires *gold*, a new currency, to trade. Gold is earned by playing the game. 
- No fractional trading exists because whole items are transacted (while there are splinters/shards, these would still represent discrete increments in currency). 
- There is currently a limit of 10 ongoing trades available at one time, as this is the maximum size of the trading window.  

Let $v_{i}(t)$ represent the holdings in currency $i$ at the $t$ timestep and $x_{i,j}(t)$ represent the amount of currency $i$ exchanged to currency $j$ at time t, with exchange rate $a_{i,j}$. To model the limited stock of each order, we use a variable $z_{i,j}$ representing the total amount of $i$ converted to $j$.

To model no fractional trading, we introduce a variable called $p_{i,j}(t)$ denoting a partial order execution of a conversion currency $i$ to $j$ at time $t$, of size $inc_{i,j}$. The variable $inc_{i,j}$ is not a decision variable but rather a fixed scalar that is found from the order book. We will restrict $p$ to be an integer, resulting in only integral trading quantities. 

To model the gold constraint, we use a variable $g(t)$ which represents the total amount of gold remaining at time $t$. Gold is lost when performing a trade $(i,j)$ with unit gold cost $cost_{i,j}$ per partial order. Because one cannot earn gold by transacting in the market, gold strictly decreases as more transactions are made. 

To model the trading window, introduce a new binary variable called $b_{i,j}(t)$ which indicates if a trade was made on the $(i,j)$ edge at time step $t$. We will restrict the sum of $b_{i,j}(t)$ for a given $t$ to be at most the $W$, the window size.  

The following construction results in a constraint that any trade made on $i,j$ at time $t$ is thus $x_{i,j}(t) = p_{i,j}(t) * b_{i,j}(t) * inc_{i,j}$. Note that this product results in a non-linear constraint, so we linearize as follows, using the big-M technique: use a new auxiliary variable $l$, and let $M_{i,j}=p_{i,j,max}$, where $M$ is the maximum number of partial orders possible. Then, 
- $l_{i,j}(t) = p_{i,j}(t)$ if $b_{i,j}(t) = 1$
- $l_{i,j}(t) = 0$ if $b_{i,j}(t) = 0$


We can then write 

$$x_{i,j}(t) = l_{i,j}(t) * inc_{i,j}$$
### Currency Arbitrage Model

```math
\eqalign{
\max_{x,v,g,p,z,l} \quad & v_{want}(T)\\
\textrm{s.t.} 
\quad & v_{have}(0) = v_0\\
\quad & g(0) = g_0 \\
\quad & x_{i,j}(t) = l_{i,j}(t) * inc_{i,j} & \forall (i,j) \in E, t \in T\\
\quad & v_{j}(t) = v_{j}(t-1) + \sum_{i \in I_{j}} a_{i,j}x_{i,j}(t) - \sum_{k \in O_j}x_{j,k}(t) & \forall j \in N, t \in T\\
\quad & g(t) = g(t-1) + \sum_{i \in I_{j}} cost(i,j) - \sum_{k \in O_j} cost(j,k) & \forall j \in N, t \in T\\
\quad & v_{j}(t-1) \geq \sum_{k \in O_{j}}x_{j,k}(t) & \forall j \in N, t \in T\\
\quad & \sum_{t=1}^{T} x_{j,k}(t) = z_{i,j} & \forall (j,k) \in E \\
\quad & z_{j,k} \leq c_{j,k} & \forall (j,k) \in E, t \in T\\
\quad & l_{i,j}(t) \leq b_{i,j}(t) * M_{i,j}\\
\quad & l_{i,j}(t) \geq p_{i,j}(t) - (1 - b_{i,j}(t)) * M\\ 
\quad & l_{i,j}(t) \geq 0 \\ 
\quad & l_{i,j}(t) \leq p_{i,j}(t)\\
\quad & \sum_{t=1}^{T} b_{i,j} \leq W\\
\quad & v_{j}(t), x_{i,j}(t), z_{i,j}, g(t) \geq 0 & \\
\quad & p_{i,j}(t) \in \mathbb{Z}^{\geq 0}
}
```

Constraints (1,2) set initial conditions. Constraint (3) enforces that trades occur in discrete (possibly partial) orders. Constraint (4,5) enforce proper balances after trades are made w.r.t to currencies and hold. Constraint (6) enforces no shorting. Constraint (7) enforces that we consider the stock of each order in the order book. Constraints (8,9,10,11) use the variable $l$ to linearize constraint (3), as described by the piecewise function above. 

## Usage 
```
python main.py -f [.csv file]
```

Alternatively, the ```src/pot/optimize.py``` directory holds the optimization functions.
## Example
An example of an optimal conversion is found in tests/currency_market.csv.

| have           | want        | ratio     | stock | gold_cost |
|----------------|-------------|-----------|-------|-----------|
| Divine Orb     | Chaos Orb   | 100.00000 | 1     | 1000      |
| Exalted Orb    | Chaos Orb   | 25.00000  | 6     | 1000      |
| Divine Orb     | Exalted Orb | 2.00000   | 4     | 1000      |
| Alteration Orb | Chaos Orb   | 0.21645   | 1386  | 1000      |

There are 4 resting orders in the order book. Suppose we have 100 chaos orbs, can make at most 10 trades with 100,000 gold. We would like to maximize the conversion from Chaos -> Divine orb. The straightforward trade places a (want=Divine, have=Chaos, ratio=.01, stock=100) order, yielding 1 divine orb. However, the optimal trade sequence is to first convert 100 chaos -> 4 exalted orb, then 4 exalted orb -> 2 divine orb. 

## Resources
- https://mobook.github.io/MO-book/notebooks/04/05-cryptocurrency-arbitrage.html#trading-and-arbitrage
- https://nbviewer.org/github/rcroessmann/sharing_public/blob/master/arbitrage_identification.ipynb#Finding-an-%22Optimal%22-Set-of-Cycles
- https://www.reddit.com/r/pathofexile/comments/1e902zz/path_of_exile_introducing_the_currency_exchange/
- https://or.stackexchange.com/questions/39/how-to-linearize-the-product-of-a-binary-and-a-non-negative-continuous-variable