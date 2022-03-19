#!/usr/bin/python -u

import os, sys, re

def cmd(c): return os.popen(c).read().strip()

sortRefs = True
matches = 0
orig = sys.argv[1]
subst= sys.argv[2]

def processMatch(matchobj):
    global matches
    matches += 1
    return subst

def processCite(matchobj):
    # Use \b and negative lookahead/lookback assertions on : to avoid partial word matches
    s = re.sub(r"\b(?<!:)" + orig + r"\b(?!:)", processMatch, matchobj.group(1))
    if sortRefs: s = ",".join(sorted([x.strip() for x in s.split(",")]))
    c = "\\cite{" + s + "}"
    #print matchobj.group(), c
    return c

files = cmd("ls -1 *.tex").split("\n")
#print "Processing:", files

for file in files:
    #print file
    fh = open(file)
    txt = fh.read()
    fh.close()
    newTxt = re.sub("\\\cite{(.*?)}", processCite, txt)
    fh = open(file, "w")
    fh.write(newTxt)
    fh.close()

print "Performed %d substitutions %s -> %s in cite commands (%d tex files)" % (matches, orig, subst, len(files))
