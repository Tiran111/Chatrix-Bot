from enum import Enum, auto

class States(Enum):
    START = auto()
    PROFILE_AGE = auto()
    PROFILE_GENDER = auto()
    PROFILE_SEEKING_GENDER = auto()
    PROFILE_CITY = auto()
    PROFILE_GOAL = auto()
    PROFILE_BIO = auto()
    ADD_MAIN_PHOTO = auto()
    
    # Адмін стани
    ADMIN_SEARCH_USER = auto()
    ADMIN_BAN_USER = auto()
    ADMIN_UNBAN_USER = auto()
    ADMIN_BAN_BY_ID = auto()
    ADMIN_BAN_BY_MESSAGE = auto()
    ADMIN_SEND_MESSAGE = auto()
    BROADCAST = auto()

# Словник для зберігання станів користувачів
user_states = {}

# Словник для зберігання даних профілів під час створення
user_profiles = {}