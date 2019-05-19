import json

import anki
from aqt import mw
from .constants import MODEL_FIELDS
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

    cardTemplate['qfmt'] = '''
    <div>
    <img id='image' style="max-height: 140px" src="">
    <h1 id="term">{{term}}</h1>
    <div class="section">
    <span class="pron"><span style="color: #777">美</span> <span id="AmEPhonetic"></span></span>
    <span class="pron"><span style="color: #777">英</span> <span id="BrEPhonetic"></span></span>
    </div>
    <div id='definitionSection' class="section" style="clear: left">
    <ul id="definitionList"></ul>
    </div>
    </div>

    <div class="section clear" style="width: 100%">
    <hr>
    </div>
    
    <div class="section clear">
    <ul id="phraseList"></ul>
    </div>

    <hr>
    
    <div class="section clear">
    <ul id="sentenceList"></ul>
    </div>
    {{Pron}}

    
    <data id="jsonString" style="display: none">{{content}}</data>
    <script>
        var jsonString = document.getElementById('jsonString').innerText
        var queryResult = JSON.parse(jsonString)
        document.getElementById('AmEPhonetic').innerText = '[' + queryResult.AmEPhonetic + ']'
        document.getElementById('BrEPhonetic').innerText = '[' + queryResult.BrEPhonetic + ']'
        var phraseUl = document.getElementById('phraseList')
        var sentenceUl = document.getElementById('sentenceList')
        addToUl(phraseUl, queryResult.phrase)
        addToUl(sentenceUl, queryResult.sentence)
    
        function addToUl(whichUl, dataList) {
            for (var i = 0; i < dataList.length; i++) {
                var li = document.createElement('li')
                var pf = document.createElement('p')
                pf.className = 'front'
                pf.innerText = dataList[i][0]
                li.appendChild(pf)
                whichUl.appendChild(li)
            }
        }
    </script>    
    '''

    cardTemplate['afmt'] = '''
    <div>
    <img id='image' style="max-height: 140px" src="{{image}}">
    <h1 id="term">{{term}}</h1>
    <div class="section">
    <span class="pron"><span style="color: #777">美</span> <span id="AmEPhonetic"></span></span>
    <span class="pron"><span style="color: #777">英</span> <span id="BrEPhonetic"></span></span>
    </div>
    <div id='definitionSection' class="section" style="clear: left">
    <ul id="definitionList"></ul>
    </div>
    </div>

    <div class="section clear" style="width: 100%">
    <hr>
    </div>
    
    <div class="section clear">
    <ul id="phraseList"></ul>
    </div>

    <hr>
    
    <div class="section clear">
    <ul id="sentenceList"></ul>
    </div>
    {{Pron}}
    
    <data id="jsonString" style="display: none">{{content}}</data>
    <script>
        var jsonString = document.getElementById('jsonString').innerText
        var queryResult = JSON.parse(jsonString)
        document.getElementById('AmEPhonetic').innerText = '[' + queryResult.AmEPhonetic + ']'
        document.getElementById('BrEPhonetic').innerText = '[' + queryResult.BrEPhonetic + ']'
        imgElement = document.getElementById('image') 
        if (Boolean(queryResult.image)){
            imgElement.setAttribute('src', queryResult.image)
        }else{
            imgElement.parentNode.removeChild(imgElement)
        }
        document.getElementById('image').setAttribute('src', queryResult.image)
        var definitionUl = document.getElementById('definitionList')
        for (var i = 0; i < queryResult.definition.length; i++) {
            var node = document.createElement('li')
            node.className = 'def'
            node.innerText = queryResult.definition[i]
            definitionUl.appendChild(node)
        }
        var phraseUl = document.getElementById('phraseList')
        var sentenceUl = document.getElementById('sentenceList')
        addToUl(phraseUl, queryResult.phrase)
        addToUl(sentenceUl, queryResult.sentence)
    
        function addToUl(whichUl, dataList) {
            for (var i = 0; i < dataList.length; i++) {
                var li = document.createElement('li')
                var pf = document.createElement('p')
                var pb = document.createElement('p')
                pf.className = 'front'
                pf.innerText = dataList[i][0]
                pb.className = 'back'
                pb.innerText = dataList[i][1]
    
                li.appendChild(pf)
                li.appendChild(pb)
                whichUl.appendChild(li)
            }
        }
    </script>
    '''

    modelObject['css'] = '''
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: left;
            color: black;
            background-color: white;
        }
         #term {
            padding-bottom: 10px;
            padding-left: 10px;
            margin: 0;
        }
        .pos {
            width: 35px;
            font-size: 93%;
            background-color: #aaa;
            color: #fff;
            line-height: 18px;
            vertical-align: middle;
            text-align: center;
            float: left;
            font-weight: bold;
        }
        .def {
            line-height: 20px;
            vertical-align: top;
            font-size: 14px;
            color: #333;
            font-weight: bold;
        }
        ul {
            clear: both;
            padding-top: 10px;
            border: 0;
            border-collapse: collapse;
            border-spacing: 0;
            list-style: none;
            margin: auto;
            padding: 0;
        }
        li {
            text-align: left;
            padding-left: 10px;
            border-left: .25em solid #dfe2e5;
        }
        image {
            display: inline;
            float: right;
            clear: both;
        }
        .section {
            margin-top: 10px;
            float: left;
        }
        .clear {
            clear: both;
        }
        .pron {
            margin-right: 5px;
            padding-left: 5px;
            float: left;
        }
        .back {
            /* padding: 10px; */
            margin-bottom: 20px;
            margin-top: -15px;
            color: #777;
        }
        hr {
            clear: left;
        }
        p {
            margin-top: 0px;
        }
    '''
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
