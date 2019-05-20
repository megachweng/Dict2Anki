import json
import os
import anki
from aqt import mw
from .constants import MODEL_FIELDS, ADDON_PATH
import logging

logger = logging.getLogger('dict2Anki.noteManager')


def getDeckList():
    return [deck['name'] for deck in mw.col.decks.all()]


def getWordsByDeck(deckName) -> [str]:
    notes = mw.col.findNotes(f'deck:"{deckName}"')
    words = []
    for nid in notes:
        note = mw.col.getNote(nid)
        if note.model().get('name', '').lower().startswith('dict2anki'):
            words += note.get('term', [])
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
    if model:
        return model
    else:
        logger.info(f'创建新模版:{modelName}')
        newModel = mw.col.models.new(modelName)
        mw.col.models.add(newModel)
        for field in MODEL_FIELDS:
            mw.col.models.addField(newModel, mw.col.models.newField(field))
        mw.col.models.update(newModel)
        return newModel


def getOrCreateModelCardTemplate(modelObject, cardTemplateName):
    logger.info(f'添加卡片类型:{cardTemplateName}')
    existingCardTemplate = modelObject['tmpls']
    if cardTemplateName in [t.get('name') for t in existingCardTemplate]:
        return
    cardTemplate = mw.col.models.newTemplate(cardTemplateName)
    with open(os.path.join(ADDON_PATH, 'template', 'front.html'), encoding='utf-8') as fp:
        cardTemplate['qfmt'] = fp.read()

    with open(os.path.join(ADDON_PATH, 'template', 'back.html'), encoding='utf-8') as fp:
        cardTemplate['afmt'] = fp.read()

    with open(os.path.join(ADDON_PATH, 'template', 'card.css'), encoding='utf-8') as fp:
        modelObject['css'] = fp.read()

    mw.col.models.addTemplate(modelObject, cardTemplate)


def addNoteToDeck(deckObject, modelObject, currentConfig: dict, oneQueryResult: dict):
    if not oneQueryResult:
        logger.warning(f'查询结果{oneQueryResult} 异常，忽略')
        return
    modelObject['did'] = deckObject['id']
    newNote = anki.notes.Note(mw.col, modelObject)

    if not currentConfig['definition']:
        oneQueryResult['definition'] = []

    if not currentConfig['phrase']:
        oneQueryResult['phrase'] = []

    if not currentConfig['sentence']:
        oneQueryResult['sentence'] = []

    if not currentConfig['image']:
        oneQueryResult['image'] = ''

    if not currentConfig['BrEPhonetic']:
        oneQueryResult['BrEPhonetic'] = 'None'

    if not currentConfig['AmEPhonetic']:
        oneQueryResult['AmEPhonetic'] = 'None'

    if not currentConfig['noPron']:
        newNote['Pron'] = f"[sound:{oneQueryResult.get('term', '')}.mp3]"

    newNote['term'] = oneQueryResult.get('term', '')
    newNote['content'] = json.dumps(oneQueryResult)

    mw.col.addNote(newNote)
    mw.col.reset()
    logger.info(f"添加笔记{newNote.get('term', '')}")
