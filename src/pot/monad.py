import pyomo.environ as pyo

"""
An implementation of a basic Pyomo monad, taken from https://mobook.github.io/MO-book/notebooks/appendix/functional-programming-pyomo.html
"""

class PyomoMonad:
    """A simple monad class for handling Pyomo operations with error handling.
    
    This class is designed to simplify Pyomo operations by providing a way to
    handle errors and chaining operations together. The bind method is used to
    chain operations, and the __call__ method is used to execute the monad.
    """

    def __init__(self, value=None, effect=None, status=None):
        """
        Initialize the PyomoMonad instance.
        
        :param value: The value to be processed by the monad
        :type value: Any
        :param effect: A function to be applied on the value
        :type effect: callable, optional
        :param status: The current status of the monad, used for error handling
        :type status: Any, optional
        """
        self.value = value
        self.status = status
        self.effect = effect

    def bind(self, func):
        """Bind a function to the current monad instance.
        
        :param func: The function to be bound to the current monad
        :type func: callable
        :return: A new PyomoMonad instance
        :rtype: PyomoMonad
        """
        if self.status is not None:
            return PyomoMonad(None, self.effect, self.status)

        try:
            result = func(self.value)
            return PyomoMonad(result, self.effect, self.status)

        except Exception as e:
            print(e)
            return PyomoMonad(None, lambda value: print(self.status), status=e)

    def __call__(self):
        """Execute the monad by calling its effect if it exists, or return its value.
        
        :return: The result of executing the monad's effect or its value
        :rtype: Any
        """
        if self.effect is not None:
            return self.effect(self.value)
        else:
            return self.value

    def __rshift__(self, func):
        """Implement the '>>' operator for chaining operations.
        
        :param func: The function to be bound to the current monad
        :type func: callable
        :return: A new PyomoMonad instance
        :rtype: PyomoMonad
        """
        return self.bind(func)
    
def Solver(s=None):
    """ Given a string solver name, try to create a pyomo.environ.SolverFactory solver. """
    if s is None:
        def func(model):
            return model.clone()
        _solver = func
    else:
        def _solver(model):
            new_model = model.clone()
            pyo.SolverFactory(s).solve(new_model)
            return new_model
    return _solver