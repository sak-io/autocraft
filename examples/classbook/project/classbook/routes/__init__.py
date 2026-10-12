"""Routers are registered here once so T3, T4 and T5 never edit the app factory together (F26).
Each task fills in only its own module."""
from . import accounts, bookings, classes

ROUTERS = [accounts.router, classes.router, bookings.router]
