from .constants import COMPATIBLE, MODEL_FIELDS, BASIC_OPTION, EXTRA_OPTION
import logging

logger = logging.getLogger('dict2Anki.noteManager')
try:
    from aqt import mw
    import anki
except ImportError:
    from test.mock_model import mw
    from test.mock_model import anki


def getDeckList():
    return [deck['name'] for deck in mw.col.decks.all()]


def getWordsByDeck(deckName) -> [str]:
    notes = mw.col.findNotes(f'deck:"{deckName}"')
    words = []
    for nid in notes:
        note = mw.col.getNote(nid)
        if note.model().get('name', '').lower().startswith('dict2anki') and note['term']:
            words.append(note['term'])
    return words


def getNotes(wordList, deckName) -> list:
    notes = []
    for word in wordList:
        note = mw.col.findNotes(f'deck:"{deckName}" term:"{word}"')
        if note:
            notes.append(note[0])
    return notes


def getOrCreateDeck(deckName):
    deck_id = mw.col.decks.id(deckName)
    deck = mw.col.decks.get(deck_id)
    mw.col.decks.save(deck)
    mw.col.reset()
    mw.reset()
    return deck


def getOrCreateModel(modelName):
    model = mw.col.models.byName(modelName)
    if (not COMPATIBLE) or (not model):
        logger.info(f'创建新模版:{modelName}')
        model = mw.col.models.new(modelName)
        mw.col.models.add(model)
        for field in MODEL_FIELDS:
            mw.col.models.addField(model, mw.col.models.newField(field))
        mw.col.models.update(model)

    return model


def getOrCreateModelCardTemplate(modelObject, cardTemplateName):
    logger.info(f'添加卡片类型:{cardTemplateName}')
    existingCardTemplate = modelObject['tmpls']
    if cardTemplateName in [t.get('name') for t in existingCardTemplate]:
        return
    cardTemplate = mw.col.models.newTemplate(cardTemplateName)
    cardTemplate['qfmt'] = '''
        <h class='term'>{{term}}</h>
        <image {{image}} height='60'>
        <div>
            <span class='phonetic'>BrE: {{BrEPhonetic}}</span>
            <span class='phonetic'>AmE: {{BrEPhonetic}}</span>
        </div>
        <div>{{phraseFront}}</div>
        <div>{{sentenceFront}}</div>
        {{BrEPron}}
        {{AmEPron}}
    '''
    cardTemplate['afmt'] = '''
        <h class='term'>{{term}}</h>
        <image {{image}} height='60'>
        <div>
            <span class='phonetic'>BrE: {{BrEPhonetic}}</span>
            <span class='phonetic'>AmE: {{BrEPhonetic}}</span>
        </div>
        <div>{{phraseBack}}</div>
        <div>{{sentenceBack}}</div>
        {{BrEPron}}
        {{AmEPron}}
    '''
    modelObject['css'] = '''
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
    mw.col.models.addTemplate(modelObject, cardTemplate)


def addNoteToDeck(deckObject, modelObject, currentConfig: dict, oneQueryResult: dict):
    modelObject['did'] = deckObject['id']

    newNote = anki.notes.Note(mw.col, modelObject)
    newNote['term'] = oneQueryResult['term']
    for configName in BASIC_OPTION + EXTRA_OPTION:
        logger.debug(f'字段:{configName}--结果:{oneQueryResult.get(configName)}')
        if oneQueryResult.get(configName):
            if configName in ['sentence', 'phrase'] and currentConfig[configName]:
                newNote[f'{configName}Front'] = '\n'.join([f'<li>{e}</li>' for e, _ in oneQueryResult[configName]])
                newNote[f'{configName}Back'] = '\n'.join([f'<li>{e}<br>{c}</li>' for e, c in oneQueryResult[configName]])
            elif configName == 'image':
                newNote[configName] = f'src="{oneQueryResult[configName]}"'
            elif configName == 'definition' and currentConfig[configName]:
                newNote[configName] = '<br>'.join(oneQueryResult[configName])
            elif currentConfig[configName]:
                newNote[configName] = oneQueryResult[configName]

    mw.col.addNote(newNote)
    mw.col.reset()
    mw.reset()


def compatTransform():
    """解决上一版本兼容问题"""
    pass
