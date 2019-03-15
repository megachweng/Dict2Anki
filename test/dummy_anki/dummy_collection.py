from test.dummy_anki.dummy_deck import Deck
from test.dummy_anki.dummy_notes import Note
from test.dummy_anki.dummy_models import Model


class Collection:
    decks = Deck
    models = Model

    @staticmethod
    def reset():
        pass

    @staticmethod
    def remNotes(*args, **kwargs):
        pass

    @staticmethod
    def getNote(nid):
        return Note(nid)

    @staticmethod
    def findNotes():
        return []
