from test.dummy_aqt.dummy_addon import AddonManager
from test.dummy_anki.dummy_collection import Collection


class mw:
    addonManager = AddonManager
    col = Collection

    @staticmethod
    def reset():
        pass


def askUser(*args, **kwargs):
    return True


def showCritical(*args, **kwargs):
    pass


def showInfo(*args, **kwargs):
    pass


def tooltip(*args, **kwargs):
    pass


def openLink(*args, **kwargs):
    pass
