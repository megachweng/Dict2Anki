from aqt import mw


def getDeckWordList(deckName):
    notes = mw.col.findNotes(f'deck:"{deckName}"')
    return [mw.col.getNote(note)['term'] for note in notes]


def getNoteByWord(words, deckName):
    def _note(word):
        try:
            return mw.col.findNotes(f'deck:"{deckName}" term:"{word}"')[0]
        except Exception:
            pass

    return [_note(word) for word in words]


def createDeck(deckName, modelName):
    # create new deck and custom model
    model = __createModel(modelName)

    deckId = mw.col.decks.id(deckName)
    deck = mw.col.decks.get(deckId)
    mw.col.reset()
    mw.reset()

    # assign custom model to new deck
    deck["mid"] = model["id"]
    mw.col.decks.save(deck)

    # assign new deck to custom model
    mw.col.models.setCurrent(model)
    mw.col.models.current()["did"] = deck["id"]
    mw.col.models.save(model)


def processNote(term, options) -> (object, str, str):
    note = mw.col.newNote()
    note["term"] = term["term"].strip()
    note["image"] = (term["image"] or '') if options['image'] else ''
    note["BrEPron"] = (term["pronunciations"]['uk_url'] or '') if options['BrEPron'] else ''
    note["AmEPron"] = (term["pronunciations"]['us_url'] or '') if options['AmEPron'] else ''
    note["BrEPhonetic"] = (term["pronunciations"]['uk_phonetic'] or '') if options["BrEPhonetic"] else ''
    note["AmEPhonetic"] = (term["pronunciations"]['us_phonetic'] or '') if options["AmEPhonetic"] else ''
    note["definitions"] = ' '.join(term['definitions'])
    note["samples"] = f'''<ul>{''.join([f"<li>{e}<br>{c}</li>" for e, c in term['samples']])}</ul>''' if options['samples'] else ''
    note["pron"] = f'[sound:bre_{term["term"]}.mp3] [sound:ame_{term["term"]}.mp3]'
    return note, (f'bre_{term["term"]}', note["BrEPron"]), (f'ame_{term["term"]}', note["AmEPron"])


def __createModel(modelName):
    md = mw.col.models
    existing = md.byName(modelName)
    if existing:
        if 'pron' not in md.fieldNames(existing):
            md.addField(existing, md.newField('pron'))
            md.update(existing)
        return existing
    m = md.new(modelName)

    # add fields
    md.addField(m, md.newField("term"))
    md.addField(m, md.newField("image"))
    md.addField(m, md.newField("definitions"))
    md.addField(m, md.newField("BrEPron"))
    md.addField(m, md.newField("AmEPron"))
    md.addField(m, md.newField("BrEPhonetic"))
    md.addField(m, md.newField("AmEPhonetic"))
    md.addField(m, md.newField("samples"))
    md.addField(m, md.newField("pron"))

    t = md.newTemplate("Normal")

    t['qfmt'] = '''
                <h class='term'>{{term}}</h>
                <br></br>
                <span>
                <img src={{image}}>
                </span>
                <div>
                <span class='phonetic'>BrE: {{BrEPhonetic}}</span>
                <span class='phonetic'>AmE: {{BrEPhonetic}}</span>
                </div>
                <hr>
                {{samples}}
                {{pron}}
                '''
    t['afmt'] = '''
                <h class='term'>{{term}}</h><br>
                <h class='term'>{{definitions}}</h>
                <br>
                <br>
                <div>
                <span class='phonetic'>BrE: {{BrEPhonetic}}</span>
                <span class='phonetic'>AmE: {{BrEPhonetic}}</span>
                </div>
                <hr>
                {{samples}}
                '''
    m['css'] = '''
                .card {
                font-family: arial;
                font-size: 20px;
                text-align: left;
                color: black;
                background-color: white;
                }
                .term {
                font-size : 35px;
                }
                .phonetic {
                margin-right:1em;

                }
            '''
    md.addTemplate(m, t)
    md.add(m)
    return m
