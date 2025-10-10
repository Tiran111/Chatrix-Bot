from enum import Enum

class States(Enum):
    """Стани користувача"""
    START = 0
    PROFILE_AGE = 1
    PROFILE_GENDER = 2
    PROFILE_SEEKING_GENDER = 3
    PROFILE_CITY = 4
    PROFILE_GOAL = 5
    PROFILE_BIO = 6
    ADD_MAIN_PHOTO = 7
    BROADCAST = 8
    ADMIN_SEARCH_USER = 9
    ADMIN_BAN_USER = 10
    ADMIN_UNBAN_USER = 11
    ADMIN_SEND_MESSAGE = 12

# Словники для зберігання станів та профілів
user_states = {}
user_profiles = {}