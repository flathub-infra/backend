from enum import Enum

# https://specifications.freedesktop.org/menu-spec/latest/apa.html


class Category(str, Enum):
    AudioVideo = "AudioVideo"
    Development = "Development"
    Education = "Education"
    Game = "Game"
    Graphics = "Graphics"
    Network = "Network"
    Office = "Office"
    Science = "Science"
    System = "System"
    Utility = "Utility"


class AppstreamType(str, Enum):
    Stable = "stable"
    Beta = "beta"
    Stable_And_Beta = "stable_and_beta"
