# Path of Trading (PoT)
## Intro
In Path of Exile (PoE) 3.25 *Settlers of Kalguur*, one of the main new features is a currency auction house which allows asynchronous trading between players. In the past, players manually traded currency.

## Background
The intention of this repo is to implement functions that assist in trading in the new PoE currency markets. Currently, the model explores two main use cases: 
- Arbitraging cross currency exchange rates: finding a sequence of trades that starts and ends at the same currency resulting in a net increase in wealth. 

- Optimal currency conversion: finding a sequence of trades that optimally converts a given amount of starting currency into a desired currency. Almost every item and commodity in PoE is priced according to *Chaos Orbs* or *Divine Orbs*, therefore currency conversion to both chaos and divine orbs is already an incredibly common task, see [here](https://poe.ninja/economy/standard/unique-weapons).

## Inputs
The model assumes input in the form of a .csv file which represents the entire order book of the currency market. Each order specifies a starting currency (called have), an ending currency (called want), a specified ratio of $\frac{want}{have}$ that prices have in terms of want, *stock* representing the quantity of the have currency, and a gold cost per each transaction.

## Model
Because the


## Usage 
## Example
