# PoeFX

# Model

For optimal currency conversion, we use a model similar to that of exercise 1.11 of Bertsimas and Tsitsiklis, *Linear Optimization*. The solution to this problem can be seen here: https://linux.ime.usp.br/~dfrever/programs/Documents/weatherwax_bertsimas_solutions_manual.pdf. 

# Use cases
- Currency arbitrage
- Optimal conversion

# Notes
Constraints unique to POE auction house: 
- Gold constraint
- Minimum trade constraints. Because we cant trade fractions of POE currency, there is a minimum increment in which transactions can be made. For instance, we could have a 2 chaos : 3 vaal exchange rate which requires conversions of 2 chaos increments to vaal. The exchange rate in this case is 1 chaos : 1.5 vaal, but we can only trade in increments of 2 chaos. Note that this is the minimum tick per partial fill possible.  
- Must constraint to have x number of available transactions.

The model is formatted according to: https://mobook.github.io/MO-book/notebooks/appendix/pyomo-style-guide.html. 

# Data format 

We assume that we are converting from currency_a to currency_b, the columns for the data are:
currency_a, currency_b, rate, increment_a, (qty_a, qty_b)

where increment_a is the trade size increment of currency_a, qty_b is the amount of currency_b that is available at the given rate

# TODO
A -> B has the ratio 2:3. This implies a going unit rate of 1:1.5, the trade increment is 2. 
