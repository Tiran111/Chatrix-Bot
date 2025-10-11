from enum import Enum

class States(Enum):
    START = 0
    PROFILE_AGE = 1
    PROFILE_GENDER = 2
    PROFILE_CITY = 3
    PROFILE_SEEKING_GENDER = 4
    PROFILE_GOAL = 5
    PROFILE_BIO = 6
    ADD_MAIN_PHOTO = 7
    ADD_PHOTO = 8
    VIEW_USER_GALLERY = 9
    ADVANCED_SEARCH_GENDER = 10
    ADVANCED_SEARCH_CITY = 11
    ADVANCED_SEARCH_CITY_INPUT = 12
    ADVANCED_SEARCH_GOAL = 13
    ADMIN_SEARCH_USER = 14
    ADMIN_BAN_USER = 15
    ADMIN_UNBAN_USER = 16
    ADMIN_SEND_MESSAGE = 17
    BROADCAST = 18
    CONTACT_ADMIN = 19  # НОВИЙ СТАН для зв'язку з адміном

# Словники для зберігання станів та профілів
user_states = {}
user_profiles = {}
gallery_view_data = {}