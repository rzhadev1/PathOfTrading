class NonIntegerStock(Exception):
    """ Raise for when an order has stock count that is not integer. """
    pass

class NonIntegerTotal(Exception):
    """ Raise for when an order has a total amount of want currency that is not integer. """
    pass