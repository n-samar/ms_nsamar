#!/usr/bin/python

import argparse, os, re, subprocess, sys, urllib
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import to_bibtex
import fuzzywuzzy.process as fwprocess
import scholar
import urwid, urwid.raw_display

## General helper functions
def cmd(c):
    f = os.popen(c)
    r = f.read()
    f.close()
    return r

# Remove list duplicates, maintain order
def uniq(l):
    seen = set()
    out = []
    for elem in l:
        if elem not in seen:
            out.append(elem)
            seen.add(elem)
    return out

def panic(err):
    print "ERROR: " + str(err)
    sys.exit(1)

flatten = lambda l : [item for sublist in l for item in sublist]

## Bibtex processing routines

def extractConfKey(key):
    elems = key.split(":")
    return elems[1] if len(elems) == 3 else None

def shortYearToFullYear(yy):
    yy = int(yy)
    if yy < 30: yy += 100  # 1930 - 2029
    return 1900 + yy

def extractYear(key):
    yys = re.findall("(?<!\d)\d{2}", key)
    return shortYearToFullYear(yys[0]) if len(yys) else 0

def extractSearchString(key):
    words = key.replace(":", " ").replace("_", " ").replace("-", " ")
    # Include the full year separate from conf name (e.g., isca08 --> isca 2008)
    def fullYear(matchobj):
        yy = int(matchobj.group(0))
        return " " + str(shortYearToFullYear(yy))
    words = re.sub("(?<!\d)\d{2}", fullYear, words)
    return words

# Takes bibtex dict as input, crossrefs it, selects appropriate fields and abbreviations, etc.
def processEntry(entry, confs):
    # Cross-reference
    conf = extractConfKey(entry["id"])
    if conf in confs:
        entry["crossref"] = conf
        confEntry = confs[conf]
        if confEntry["type"] == "proceedings":
            entry["type"] = "inproceedings"
        
        # Remove common fields
        confEntryFields = set(confEntry.keys())
        confEntryFields.remove("id")
        confEntryFields.remove("type")
        for key in entry.keys():
            if key in confEntryFields:
                del entry[key]

    # Filter fields
    commonFields = ["type", "id", "author", "title", "year", "crossref"]
    filterDict = {
        "inproceedings" : set(commonFields + ["booktitle"]),
        "article" : set(commonFields + ["journal", "volume", "number"]),
    }

    entry["type"] = entry["type"].lower()
    if entry["type"] == "conference": entry["type"] = "inproceedings"

    if entry["type"] in filterDict:
        filterSet = filterDict[entry["type"]]
        for key in entry.keys():
            if key not in filterSet:
                del entry[key]

    # Preserve title capitalization
    if "title" in entry:
        title = entry["title"].strip()
        while title.startswith("{"): title = title[1:].strip()
        while title.endswith("}"): title = title[:-1].strip()
        entry["title"] = "{" + title + "}"
    else:
        print "ERROR:", entry
        sys.exit(1)

    # TODO: Capitalize common words properly (QoS, DRAM, CMP, ...)
    # TODO: Abbreviations

    return entry

# Hack to sidestep a bug in BibTexParser
# TODO: The whole BibTexParser class is awkward; should just abstract it & avoid the hacks needed to use it
class BibParser(BibTexParser):
    def _add_val(self, val):
        """ Clean instring before adding to dictionary

        :param val: a value
        :type val: string
        :returns: string -- value
        """
        if not val or val == "{}":
            return ''
        val = self._strip_braces(val)
        val = self._strip_quotes(val)
        # dsm: Commented out, this cleans out double braces,
        # which we use to preserve caps
        #val = self._strip_braces(val)
        val = self._string_subst(val)
        return val

def bibToTxt(bib):
    bp = BibParser("")
    bp.records = [bib]
    bp.entries_hash = {}
    return to_bibtex(bp)

def txtToBib(txt):
    bp = BibParser(txt)
    if len(bp.records):
        return bp.records[0]
    else:
        return {"type" : "inproceedings", "id": "parsingError"}

## Search 

def gsQuery(words, results=5):
    scholar.ScholarConf.COOKIE_JAR_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "gs_cookie.txt")
    querier = scholar.ScholarQuerier()
    settings = scholar.ScholarSettings() 
    settings.set_citation_format(scholar.ScholarSettings.CITFORM_BIBTEX)
    querier.apply_settings(settings)

    query = scholar.SearchScholarQuery()
    query.set_words(words)
    query.set_num_page_results(results)

    querier.send_query(query)
    return [art.as_citation() for art in querier.articles]

def incrementalQuery(words):
    # Go through Google (better matches)
    ua = "Mozilla/5.0 (X11; Linux x86_64; rv:28.0) Gecko/20100101  Firefox/28.0"
    url = "https://www.google.com/search?" + urllib.urlencode({'q': words})
    results = cmd('wget -O- -q --user-agent "%s" %s' % (ua, url))

    related = re.findall(r'related:[a-zA-Z0-9_-]+:scholar.google.com', results)
    hits = uniq(related)

    # Return results one by one (save queries, and typ. the first one is right)
    for hit in hits:
        yield gsQuery(hit, 1)

    if len(hits) < 5:
        yield gsQuery(words, 5 - len(hits))

# Maintains state associated with a single entry, including current search results and bibtex
class BibEntry:
    def __init__(self, key, defEntry, confs):
        self.key = key
        self.confs = confs
        if defEntry == None:
            defEntry = {"type" : "inproceedings", "id" : key, "author" : "", "title" : ""}
            year = extractYear(key)
            if year: defEntry["year"] = str(year)
        self.results = [(bibToTxt(defEntry), processEntry(defEntry, self.confs))]
        self.searchState = ("", None)

    def changeKey(self, newKey):
        self.key = newKey
        for res in self.results:
            res[1]["id"] = newKey

    # Returns true if it added more results
    def search(self, words):
        (curWords, curGen) = self.searchState
        if words != curWords:
            self.results = [self.results[0]]
            self.searchState = (words, incrementalQuery(words))
            return self.search(words)
        else:
            if curGen is None: return False
            try:
                for txt in curGen.next():
                    bib = txtToBib(txt)
                    bib["id"] = self.key
                    bib = processEntry(bib, self.confs)
                    self.results.append((txt, bib))
                return True
            except StopIteration:
                self.searchState = (words, None)
                return False

    def numResults(self):
        return len(self.results)

    def getShortname(self, idx):
        bib = self.results[idx][1]
        res = bib["title"] if "title" in bib else ""
        res = res.replace("{", "").replace("}", "")
        if idx == 0 and len(res) == 0:
            return "Default entry"
        elif idx == 0:
            res = "Current entry: " + res 
        else:
            if len(res) == 0: res = "Result " + str(idx)
        return res

    def getOrigText(self, idx):
        return self.results[idx][0]

    def getProcessedText(self, idx):
        bib = self.results[idx][1]
        txt = bibToTxt(bib)
        if "crossref" in bib:
            crossref = bib["crossref"]
            if crossref in self.confs:
                txt += "\n\n% Crossref entry:\n"
                txt += bibToTxt(self.confs[crossref])
            else:
                txt += "\n\n% WARNING: Missing crossref"
        return txt

    def _comment(self, txt):
        return "\n".join([("" if line.startswith("%") else "% ") + line for line in txt.split("\n")])

    def _stripCommentLines(self, txt):
        return "\n".join([line for line in txt.split("\n") if not line.strip().startswith("%")])

    def getEditText(self, idx):
        bib = dict(self.results[idx][1])
        bib["id"] = self.key
        txt = bibToTxt(bib)
        txt += "\n\n% Comments and changes to the key will be ignored"
        txt += "\n% Original entry:\n"
        txt += self._comment(self.getOrigText(idx))
        txt += "%\n% Processed entry:\n"
        txt += self._comment(self.getProcessedText(idx))
        return txt

    def setProcessedEntry(self, idx, txt):
        try:
            bib = txtToBib(self._stripCommentLines(txt))
        except:
            return False
        bib["id"] = self.key
        self.results[idx] = (self.results[idx][0], bib)
        return True


# Keeps track of missing entries, updates key changes
class BibData:
    def __init__(self, texFiles, refsFile, confsFile, mode):
        cbibfile = open(confsFile, 'r')
        cbp = BibParser(cbibfile.read())
        cbibfile.close()
        self.confs = cbp.get_entry_dict()

        self.refsFile = refsFile
        bibfile = open(refsFile, 'r')
        self.bp = BibParser(bibfile.read())
        bibfile.close()
        refs = self.bp.get_entry_dict()

        self.texFiles = texFiles
        self.updateCites()
        
        keys = uniq(self.cites)

        if mode == "missing":
            targetKeys = [key for key in keys if key not in refs]
        elif mode in ("cited", "cdiff"):
            targetKeys = sorted(keys)
        elif mode in ("all", "adiff"):
            targetKeys = sorted(list(set(keys + refs.keys())))
        elif mode == "aux":
            keysStr = cmd('bibtex *.aux | grep "didn\'t find a" | cut -f2 -d\\"').strip()
            targetKeys = keysStr.split("\n") if len(keysStr) else []
        else:
            panic("Invalid mode: " + str(mode))
        
        self.entries = [BibEntry(key, refs[key] if key in refs else None, self.confs) for key in targetKeys]

        if mode.endswith("diff"):
            # Skip entries that already match our format
            print sorted(targetKeys)
            self.entries = [e for e in self.entries if ((e.results[0][0] != bibToTxt(e.results[0][1])) or (e.key not in refs))]

        self.stats = (len(self.cites), len(keys), len(texFiles), len(self.entries), len(refs), len(self.confs))

    def updateCites(self):
        cites = []
        self.texFiles = texFiles
        for texFile in texFiles:
            f = open(texFile, "r")
            tex = f.read()
            f.close()
            citegroups = re.findall("\\\cite{(.*?)}", tex, flags=re.MULTILINE | re.DOTALL)
            #print texFile, citegroups
            def trimCite(c):
                #return c.strip() # doesn't handle comments well
                lines = c.split("\n")
                # Strip comments
                fcc = [re.sub(r"%(.*)", "", l) for l in lines]
                res = " ".join(fcc).strip()
                # A cite with a pre or post comment is clean, and a commented citation
                # results in a zero-length string that's removed later
                return res
            cites += flatten([[trimCite(c) for c in cg.split(",")] for cg in citegroups])
        cites = [c for c in cites if len(c)]
        self.cites = cites

        self.citeCounts = {}
        for c in cites:
            if c not in self.citeCounts:
                self.citeCounts[c] = 0
            self.citeCounts[c] += 1

    def getCiteCount(self, key):
        return self.citeCounts[key] if key in self.citeCounts else 0

    def numEntries(self):
        return len(self.entries)

    def entry(self, idx):
        return self.entries[idx]

    def getSimilarKeys(self, key):
        matches = fwprocess.extract(key, self.bp.get_entry_dict().keys(), limit=3)
        return [mkey for (mkey, mscore) in matches if mscore > 50 and mkey != key]

    # Both of these need caller to drop refs to entry objects, and check if the length has changed

    def changeKey(self, idx, newKey):
        assert idx < len(self.entries)
        origKey = self.entries[idx].key
        if newKey in self.bp.get_entry_dict():
            # Other entry wins
            self.entries.pop(idx)
        else:
            for i in range(idx, len(self.entries)):
                if self.entries[i].key == newKey:
                    self.entries.pop(i)
            hasKey = False
            for e in self.entries:
                if e.key == newKey:
                    hasKey = True
                    break
            if hasKey:
                self.entries.pop(idx)
            else:
                self.entries[idx].changeKey(newKey)

        # Update refs file
        if origKey in self.bp.get_entry_dict():
            if newKey in self.bp.get_entry_dict():
                # Other entry wins, delete this one
                recs = self.bp.get_entry_list()
                for i in range(len(recs)):
                    if recs[i]["id"] == origKey:
                        recs.pop(i)
                        break
                self.bp.records = recs
            else:
                # Rename to new key
                self.bp.get_entry_dict()[origKey]["id"] = newKey
            self.bp.entries_hash = {} # clear dict (HACK)
            assert newKey in self.bp.get_entry_dict()
            self.writeRefs()

        # Update tex files
        def processCite(matchobj):
            # Use \b and negative lookahead/lookback assertions on : to avoid partial word matches
            s = re.sub(r"\b(?<!:)" + origKey + r"\b(?!:)", lambda x: newKey, matchobj.group(1))
            c = "\\cite{" + s + "}"
            return c

        for file in self.texFiles:
            fh = open(file)
            txt = fh.read()
            fh.close()
            newTxt = re.sub("\\\cite{(.*?)}", processCite, txt, flags=re.MULTILINE | re.DOTALL)
            fh = open(file, "w")
            fh.write(newTxt)
            fh.close()

        # Re-scans tex files; must be called after updating them
        self.updateCites()
    
    def writeRefs(self):
        txt = to_bibtex(self.bp)
        bibfile = open(self.refsFile, 'w')
        bibfile.write(txt.encode("utf-8"))
        bibfile.close()

    def saveAndRemove(self, idx, resIdx):
        assert idx < len(self.entries)
        entry = self.entries[idx]
        assert resIdx < len(entry.results)
        bib = entry.results[resIdx][1]
        assert bib["id"] == entry.key
        
        if entry.key not in self.bp.get_entry_dict():
            self.bp.records += [bib]
        else:
            self.bp.get_entry_dict()[entry.key] = bib
        self.bp.entries_hash = {}
        self.writeRefs()

        self.entries.pop(idx)

    def remove(self, idx):
        assert idx < len(self.entries)
        self.entries.pop(idx)


class UI:
    def __init__(self, bibdata):
        self.bibdata = bibdata
        self.headerText = urwid.Text("")
        self.entryText = urwid.Text("")
        self.similarEntries = urwid.Columns([])
        self.searchBox = urwid.Edit([("default", "Search: ")], "")
        self.searchIcon = urwid.SelectableIcon("+ results", 0)
        self.origBib = urwid.Text("")
        self.procBib = urwid.Text("")

        blank = urwid.Divider()

        leftPaneElems = [
            blank,
            self.entryText,
            self.similarEntries,
            blank,
            urwid.AttrMap(urwid.SelectableIcon("* Default entry", 0), None, "selected"),
            blank,
            urwid.AttrMap(self.searchBox, "editbg", "editfg"),
            urwid.AttrMap(self.searchIcon, None, "selected")
        ]

        self.searchList = urwid.SimpleListWalker(leftPaneElems)
        self.searchListOffset = len(leftPaneElems)-1 # first search result at this offset
        self.searchListSimilarPos = 2
        self.searchListDefPos = 4

        leftPane = urwid.ListBox(self.searchList)

        rightPaneElems = [
            urwid.LineBox(urwid.Filler(self.origBib), "Bibtex entry", tline = " ", lline = " ", rline = " ", bline = " "),
            urwid.LineBox(urwid.Filler(self.procBib), "Processed bibtex entry", tline = " ", lline = " ", rline = " ", bline = " "),
        ]
        
        rightPane = urwid.AttrMap(urwid.Pile(rightPaneElems), "bibpane")
        
        mainPane = urwid.Columns([leftPane, rightPane])

        footerTxt = "Scroll down to search | I: Ignore | S: Save | K: Change key | E: Edit | Q: Quit"
        self.win = urwid.Frame(mainPane,
                header = urwid.AttrMap(self.headerText, "footer"),
                footer = urwid.AttrMap(urwid.Text(footerTxt, align = "center"), "footer"))

        # State for updates
        self.startEntries = bibdata.numEntries()
        self.prevSearchText = ""
        self.skipCallback = False

        urwid.connect_signal(self.searchList, 'modified', lambda: self.scrollCallback())

    def exit(self):
        # vim messes up term colors, so reset
        #subprocess.call("reset", shell=False)
        raise urwid.ExitMainLoop()

    # Returns -1 if invalid
    def getSelectedResIdx(self):
        if self.bibdata.numEntries() == 0: return -1
        entry = self.bibdata.entry(0)
        focusPos = self.searchList.focus
        if focusPos == self.searchListDefPos or (focusPos >= self.searchListOffset and focusPos < len(self.searchList)-1):
            resIdx = 0 if focusPos == self.searchListDefPos else (focusPos - self.searchListOffset + 1)
            assert resIdx < entry.numResults()
            return resIdx
        else:
            return -1

    def update(self, updateResults, updateEntryFields):
        bd = self.bibdata
        if bd.numEntries() == 0: self.exit()
        entry = bd.entry(0)

        # Avoid loops between update() and scrollCallback()
        self.skipCallback = True
        
        if updateEntryFields:
            self.headerText.set_text("BIBDATA - Entry %d/%d" % (self.startEntries - bd.numEntries() + 1, self.startEntries))
            self.entryText.set_text("Entry: " + entry.key + " (" + str(self.bibdata.getCiteCount(entry.key)) + " cites)")

            similarKeys = self.bibdata.getSimilarKeys(entry.key)
            self.similarEntries.contents = []
            if len(similarKeys):
                self.similarEntries.contents.append((urwid.Text("Close matches:"), ("pack", 0, False)))
                for k in similarKeys:
                    self.similarEntries.contents.append(
                            (urwid.AttrMap(urwid.SelectableIcon(" " + k, 0), None, "selected"), ("pack", 0, False)))
                self.similarEntries.set_focus(1)  # needed to make Columns selectable

            self.searchBox.set_edit_text(extractSearchString(entry.key))
            self.searchList[self.searchListDefPos].original_widget.set_text("* " + entry.getShortname(0))

            self.searchList.set_focus(self.searchListDefPos)

        if updateResults:
            numResults = entry.numResults() - 1
            paneResults = len(self.searchList) - self.searchListOffset - 1
            while numResults > paneResults:
                self.searchList.insert(-1, urwid.AttrMap(urwid.SelectableIcon("* Search result", 0), None, "selected"))
                paneResults += 1
            while numResults < paneResults:
                self.searchList.pop(-2)
                paneResults -= 1
            for i in range(1, entry.numResults()):
                name = entry.getShortname(i)
                self.searchList[self.searchListOffset + i - 1].original_widget.set_text("* " + name)
            if self.searchList.focus == len(self.searchList) - 1:
                self.searchList.set_focus(self.searchList.focus - 1)

        resIdx = self.getSelectedResIdx()
        if resIdx >= 0:
            self.origBib.set_text(entry.getOrigText(resIdx))
            self.procBib.set_text(entry.getProcessedText(resIdx))

        if self.searchBox.get_edit_text() != self.prevSearchText:
            self.searchIcon.set_text("+ results")
            self.prevSearchText = self.searchBox.get_edit_text()
        
        self.skipCallback = False

    def scrollCallback(self):
        if self.skipCallback: return

        focusPos = self.searchList.focus
        if focusPos == len(self.searchList) - 1:
            self.searchIcon.set_text("+ searching...")
            self.loop.draw_screen()
            res = self.bibdata.entry(0).search(self.searchBox.get_edit_text())
            if res:
                self.searchIcon.set_text("+ results")
            else:
                self.searchIcon.set_text("- no more results")
            self.update(True, False)
        else:
            self.update(False, False)

    def run(self):
        self.keybox = None

        def handleKey(key):
            if key in ('q', 'Q'):
                self.exit()
            elif key in ('i', 'I'):
                self.bibdata.remove(0)
                self.update(True, True)
            elif key in ('s', 'S'):
                resIdx = self.getSelectedResIdx()
                if resIdx >= 0:
                    self.bibdata.saveAndRemove(0, resIdx)
                    self.update(True, True)
            elif key in ('e', 'E'):
                resIdx = self.getSelectedResIdx()
                if resIdx >= 0:
                    editTxt = self.bibdata.entry(0).getEditText(resIdx)
                    tmpfile = ".tmp_bibdata.bib"
                    f = open(tmpfile, "w")
                    f.write(editTxt)
                    f.close()
                    editor = os.environ["EDITOR"] if "EDITOR" in os.environ else ""
                    if len(editor) == 0:
                        # Use THE sensible default (really, I should do y'all a
                        # favor and change $EDITOR to vim)
                        editor = "vim"

                    # stop/start avoid the editor's terminal modes polluting ours
                    self.screen.clear()
                    self.screen.stop()
                    os.system(editor + " " + tmpfile)
                    self.screen.start()
                    self.screen.clear()
                    self.loop.draw_screen()
                    
                    f = open(tmpfile, "r")
                    editTxt = f.read()
                    f.close()
                    os.remove(tmpfile)
                    self.bibdata.entry(0).setProcessedEntry(resIdx, editTxt)
                    self.update(True, True)
            elif key in ('k', "K"):
                assert self.keybox == None
                # Use current key by default, or a similar match if it's currently on focus
                keyTxt = self.bibdata.entry(0).key
                if self.searchList.focus == self.searchListSimilarPos:
                    focusIcon = self.similarEntries.get_focus()
                    if focusIcon:
                        keyTxt = focusIcon.original_widget.get_text()[0].strip()

                self.keybox = urwid.Edit("", keyTxt, align="center")
                self.loop.widget = urwid.Overlay(urwid.Filler(
                    urwid.LineBox(urwid.Pile([urwid.AttrMap(self.keybox, "editbg", "editfg"),
                        urwid.Text("Updates tex & bib files\nIf same-key entry exists, that entry is used\nEnter: Accept | Esc: Cancel", align="center")]), "Change entry key")
                    ), self.win, "center", 50, "middle", 7)
                self.loop.draw_screen()
            elif key in ("enter", "esc") and self.keybox is not None:
                if key == "enter":
                    newKey = self.keybox.get_edit_text()
                    self.bibdata.changeKey(0, newKey)
                    self.update(True, True)
                self.keybox = None
                self.loop.widget = self.win
                self.loop.draw_screen()

        palette = [
            (None, 'light gray', 'black', 'light gray', 'light gray', 'black'),
            ("footer", 'white', 'black', 'white', 'white', 'g7'),
            ("bibpane", 'light gray', 'black', 'light gray', 'light gray', 'g3'),
            ('editfg','white', 'dark blue', 'bold', 'white', '#006'),
            ('editbg','light gray', 'dark blue', "light gray", 'light gray', '#006'),
            ("selected", 'white,bold', 'black', 'white', 'white', 'g3'),
        ]

        screen = urwid.raw_display.Screen()
        screen.set_terminal_properties(256)
        screen.register_palette(palette)
        #screen.set_mouse_tracking(False)
        self.screen = screen

        self.update(False, True)

        self.loop = urwid.MainLoop(self.win, screen = screen, unhandled_input = handleKey)
        self.loop.run()

if __name__ == "__main__":
    args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    args.add_argument("-m", "--mode", type=str, default="missing", help="Select entries to process ('missing': cited entries not in refs; " \
            "'diff' : missing + cited entries that change after processing; 'cited': all cited entries; 'all' : all missing entries and all entries in the refs file); " \
            "'aux' : determine by scanning aux files")
    args.add_argument("-b", "--bibfile", type=str, default="refs.bib", help="Refs bibfile")
    args.add_argument("-c", "--confs", type=str, default="confs.bib", help="Confs bibfile (for automatic cross-referencing)")
    args.add_argument("texfiles", type=str, default="", nargs="*", help="Latex files to process (all .tex files in cwd by default)")
    args = args.parse_args()

    texFiles = args.texfiles
    if texFiles == "":
        texFiles = [fn for fn in cmd("ls -1 *.tex").strip().split("\n") if len(fn)]

    for file in [args.bibfile, args.confs] + texFiles:
        if not os.path.exists(file):
            panic("Missing input file: " + str(file))

    bibdata = BibData(texFiles, args.bibfile, args.confs, args.mode)
    print "%d citations to %d entries in %d tex files | %d entries need processing | %d ref entries | %d conf entries" % bibdata.stats
    if bibdata.numEntries():
        ui = UI(bibdata)
        ui.run()
