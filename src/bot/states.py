"""FSM states for bot"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Registration flow states"""
    waiting_for_organization = State()


class OrderStates(StatesGroup):
    """Order flow states"""
    waiting_for_order = State()
    waiting_for_confirmation = State()
    waiting_for_admin = State()

