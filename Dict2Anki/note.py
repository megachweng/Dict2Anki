# Anki
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip

class Note(object):
    def __init__(self, new, deleted,syncSettings):
        self.new = new
        self.deleted = deleted
        self.syncSettings = syncSettings
    def addCustomModel(self, name, col):
        """create a new custom model for the imported deck"""
        mm = col.models
        existing = mm.byName("Dict2Anki")
        if existing:
            return existing
        m = mm.new("Dict2Anki")
        m['css'] = """.card{font-family:arial;font-size:14px;text-align:left;color:#212121;background-color:white}.pronounce{line-height:30px;font-size:24px;margin-bottom:0}.phonetic{font-size:14px;font-family:"lucida sans unicode",arial,sans-serif;color:#01848f}.term{margin-bottom:-5px}.divider{margin:1em 0 1em 0;border-bottom:2px solid #4caf50}.phrase,.sentence{color:#01848f;padding-right:1em}tr{vertical-align:top}"""

        # add fields
        mm.addField(m, mm.newField("term"))
        mm.addField(m, mm.newField("definition"))
        mm.addField(m, mm.newField("uk"))
        mm.addField(m, mm.newField("us"))
        mm.addField(m, mm.newField("phrase0"))
        mm.addField(m, mm.newField("phrase1"))
        mm.addField(m, mm.newField("phrase2"))
        mm.addField(m, mm.newField("phrase_explain0"))
        mm.addField(m, mm.newField("phrase_explain1"))
        mm.addField(m, mm.newField("phrase_explain2"))
        mm.addField(m, mm.newField("sentence0"))
        mm.addField(m, mm.newField("sentence1"))
        mm.addField(m, mm.newField("sentence2"))
        mm.addField(m, mm.newField("sentence_explain0"))
        mm.addField(m, mm.newField("sentence_explain1"))
        mm.addField(m, mm.newField("sentence_explain2"))
        mm.addField(m, mm.newField("pplaceHolder0"))
        mm.addField(m, mm.newField("pplaceHolder1"))
        mm.addField(m, mm.newField("pplaceHolder2"))
        mm.addField(m, mm.newField("splaceHolder0"))
        mm.addField(m, mm.newField("splaceHolder1"))
        mm.addField(m, mm.newField("splaceHolder2"))
        mm.addField(m, mm.newField("image"))
        mm.addField(m, mm.newField("pronunciation"))

        # add cards
        t = mm.newTemplate("Normal")
        t['qfmt'] = """\
            <table>
            <tr>
            <td>
            <h1 class="term">{{term}}</h1>
                <span>{{pronunciation}}</span>
                <div class="pronounce">
                    <span class="phonetic">UK[{{uk}}]</span>
                    <span class="phonetic">US[{{us}}]</span>
                </div>
                <div class="definiton">Tap To View</div>
            </td>
            <td>
                {{image}}
            </td>
            </tr>
            </table>
            <div class="divider"></div>
            <table>
                <tr><td class="phrase">{{phrase0}}</td><td>{{pplaceHolder0}}</td></tr>
                <tr><td class="phrase">{{phrase1}}</td><td>{{pplaceHolder1}}</td></tr>
                <tr><td class="phrase">{{phrase2}}</td><td>{{pplaceHolder2}}</td></tr>
            </table>
            <table>
                <tr><td class="sentence">{{sentence0}}</td><td>{{splaceHolder0}}</td></tr>
                <tr><td class="sentence">{{sentence1}}</td><td>{{splaceHolder1}}</td></tr>
                <tr><td class="sentence">{{sentence2}}</td><td>{{splaceHolder2}}</td></tr>
            </table>
        """
        t['afmt'] = """\
            <table>
            <tr>
            <td>
            <h1 class="term">{{term}}</h1>
                <span>{{pronunciation}}</span>
                <div class="pronounce">
                    <span class="phonetic">UK[{{uk}}]</span>
                    <span class="phonetic">US[{{us}}]</span>
                </div>
                <div class="definiton">{{definition}}</div>
            </td>
            <td>
                {{image}}
            </td>
            </tr>
            </table>
            <div class="divider"></div>
            <table>
                <tr><td class="phrase">{{phrase0}}</td><td>{{phrase_explain0}}</td></tr>
                <tr><td class="phrase">{{phrase1}}</td><td>{{phrase_explain1}}</td></tr>
                <tr><td class="phrase">{{phrase2}}</td><td>{{phrase_explain2}}</td></tr>
            </table>
            <table>
                <tr><td class="sentence">{{sentence0}}</td><td>{{sentence_explain0}}</td></tr>
                <tr><td class="sentence">{{sentence1}}</td><td>{{sentence_explain1}}</td></tr>
                <tr><td class="sentence">{{sentence2}}</td><td>{{sentence_explain2}}</td></tr>
            </table>
        """

        mm.addTemplate(m, t)
        mm.add(m)
        return m

    def processNote(self, deckName):
        deck = mw.col.decks.get(mw.col.decks.id(deckName))

        # create custom model
        model = self.addCustomModel(deckName, mw.col)

        # assign custom model to new deck
        mw.col.decks.select(deck["id"])
        mw.col.decks.get(deck)["mid"] = model["id"]
        mw.col.decks.save(deck)

        # assign new deck to custom model
        mw.col.models.setCurrent(model)
        mw.col.models.current()["did"] = deck["id"]
        mw.col.models.save(model)

        # start creating notes
        if self.new:
            for term in self.new:
                note = mw.col.newNote()
                note['term'] = term['term']
                if term['definition']:
                    note['definition'] = term['definition']
                if term['uk']:
                    note['uk'] = term['uk']
                if term['us']:
                    note['us'] = term['us']
                if self.syncSettings['pronunciation']:
                    note['pronunciation'] = "[sound:MG-"+term['term']+".mp3]"
                if term['phrases']:
                    for index, phrase in enumerate(term['phrases']):
                        note['phrase' + str(index)] = phrase
                        note['phrase_explain' + str(index)] = term['phrases_explains'][index]
                        note['pplaceHolder' + str(index)] = "Tap To View"

                if term['sentences']:
                    for index, sentence in enumerate(term['sentences']):
                        note['sentence' + str(index)] = sentence
                        note['sentence_explain' + str(index)] = term['sentences_explains'][index]
                        note['splaceHolder' + str(index)] = "Tap To View"

                if term['image']:
                    if self.syncSettings['saveImage']:
                        note['image'] = """<div><img src="MG-{}.jpg" /></div>""".format(term['term'])
                    else:
                        note['image'] = "<img src ='{}' />".format(term['image'])
                    mw.app.processEvents()
                mw.col.addNote(note)
            mw.col.reset()
            mw.reset()

        # start deleting notes

        if self.deleted:
            for term in self.deleted:
                cardID = mw.col.findCards("term:" + term )
                deckID = mw.col.decks.id(deckName)
                for cid in cardID:
                    nid = mw.col.db.scalar("select nid from cards where id = ? and did = ?", cid, deckID)
                    if nid is not None:
                        mw.col.db.execute("delete from cards where id =?", cid)
                        mw.col.db.execute("delete from notes where id =?", nid)
            mw.col.fixIntegrity()
            mw.col.reset()
            mw.reset()
        tooltip('Added : ' + str(len(self.new)) + '<br><br>Deleted : ' + str(len(self.deleted)), period=3000)
