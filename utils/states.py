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
    CONTACT_ADMIN = 10
    SEND_MESSAGE = 11
    
    # Адмін стани
    ADMIN_BAN_USER = 100
    ADMIN_UNBAN_USER = 101
    BROADCAST = 102
    ADMIN_SEARCH_USER = 103
    
    # Розширений пошук
    ADVANCED_SEARCH_GENDER = 200
    ADVANCED_SEARCH_CITY = 201
    ADVANCED_SEARCH_CITY_INPUT = 202
    ADVANCED_SEARCH_GOAL = 203

# Словники для зберігання станів користувачів
user_states = {}
user_profiles = {}
gallery_view_data = {}