class deck:
    pass


class collection:
    decks = deck


class note:
    def Note(self):
        pass


class anki:
    notes = note


class mw:
    col = collection

    @classmethod
    def reset(cls):
        pass
