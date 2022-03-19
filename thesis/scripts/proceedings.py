#!/usr/bin/python -u

import string
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import to_bibtex

maxYear = 2021
def sincen(year, cadence): return range(year, maxYear+1, cadence)
def since(year): return sincen(year, 1)

# See http://stackoverflow.com/a/20007730
ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

# See http://code.activestate.com/recipes/81611-roman-numerals/
def roman(input):
    if type(input) != type(1):
       raise TypeError, "expected integer, got %s" % type(input)
    if not 0 < input < 4000:
       raise ValueError, "Argument must be between 1 and 3999"   
    ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
    nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
    result = ""
    for i in range(len(ints)):
        count = int(input / ints[i])
        result += nums[i] * count
        input -= ints[i] * count
    return result

# Each entry is tag, years, starting number, short name, long name
# Template elements:
# $N - numeral, $NTH - ordinal, $RN - roman numeral
# $YY - 2-digit year, $YYYY - 4-digit
# Gathered mostly from http://www.informatik.uni-trier.de/~ley/db/conf
conferences = [
("isca", [1973, 1974] + since(1976), 1, "ISCA-$N", "$NTH annual International Symposium on Computer Architecture"),
("micro", range(1968, 1990+1), 1, "MICRO-$N", "$NTH annual workshop and symposium on Microprogramming and Microarchitecture"),
("micro", since(1991), 24, "MICRO-$N", "$NTH annual IEEE/ACM international symposium on Microarchitecture"),
("asplos", [1982, 1987, 1989, 1991] + range(1992, 2006+1, 2) + since(2008), 1, "ASPLOS-$RN", "$NTH international conference on Architectural Support for Programming Languages and Operating Systems"),
("hpca", since(1995), 1, "HPCA-$N", "$NTH IEEE international symposium on High Performance Computer Architecture"),
# PACT was held in 1993 and 1994 as the IFIP WG10.3 Working Conference on ... various things. Then they started at 5. Very logical.
("pact", since(1996), 5, "PACT-$N", "$NTH International Conference on Parallel Architectures and Compilation Techniques"),

("sc", since(1988), 1, "SC$YY", "ACM/IEEE conference on Supercomputing"), # SC changes the full name almost every year... wtf?
("ics", since(1987), 1, "ICS'$YY", "International Conference on Supercomputing"),
("iccd", since(1983), 1, "ICCD", "$NTH International Conference on Computer Design"),
("hipeac", [2005] + since(2007), 1, "HiPEAC", "$NTH international conference on High Performance Embedded Architectures and Compilers"),
("ipdps", since(2000), 14, "IPDPS", "$NTH IEEE International Parallel and Distributed Processing Symposium"), # previously IPPS
("iiswc", since(2006), 1, "IISWC", "IEEE International Symposium on Workload Characterization"),
("ispass", [2001, 2002] + since(2003), 1, "ISPASS", "IEEE International Symposium on Performance Analysis of Systems and Software"),

("sosp", sincen(1967, 2), 1, "SOSP-$N", "$NTH Symposium on Operating System Principles"),
("osdi", [1994, 1996, 1999] + sincen(2000, 2), 1, "OSDI-$N", "$NTH USENIX symposium on Operating Systems Design and Implementation"),
("usenix", since(1994), 1, "USENIX ATC", "USENIX Annual Technical Conference"),
("nsdi", since(2004), 1, "NSDI", "$NTH USENIX Symposium on Networked Systems Design and Implementation"),
("eurosys", since(2006), 1, "EuroSys", "EuroSys Conference"),

("isscc", since(1954), 1, "ISSCC", "IEEE International Solid-State Circuits Conference"),
("dac", since(1964), 1, "DAC-$N", "$NTH Design Automation Conference"),
("date", since(1998), 1, "DATE", "Design, Automation and Test in Europe"),

("pldi", since(1988), 1, "PLDI", "ACM SIGPLAN Conference on Programming Language Design and Implementation"),
("ppopp", since(1990), 1, "PPoPP", "ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming"),
("popl", [1973] + since(1975), 1, "POPL", "$NTH ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages"),
("oopsla", since(1986), 1, "OOPSLA", "ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications"),
("spaa", since(1989), 1, "SPAA", "$NTH ACM Symposium on Parallelism in Algorithms and Architectures"),
("cgo", since(2003), 1, "CGO", "$NTH IEEE/ACM International Symposium on Code Generation and Optimization"),

("sigcomm", since(1985), 1, "SIGCOMM", "ACM SIGCOMM Conference"),
]

cfull = []
clong = []
cshort = []

abbrvs =  [
("proceedings", "proc"),
("international", "intl"),
("conference", "conf"),
("symposium", "symp"),
]
abbrvs += [(f.capitalize(), a.capitalize()) for (f, a) in abbrvs]

def abbreviate(s):
    for (f, a) in abbrvs:
        s = s.replace(f, a + ".")
    return s

def genEntry(id, year, booktitle):
    return {"type" : "proceedings", "id" : id, "booktitle" : abbreviate(booktitle), "year" : str(year)}

for (key, years, start, shortname, longname) in conferences:
    n = start
    for year in years:
        shortyear = str(year)[-2:]
        subs = {"N" : str(n), "NTH" : ordinal(n), "RN" : roman(n), "YYYY": str(year), "YY" : shortyear}
        
        id = key + shortyear
        shortbt = string.Template(shortname).substitute(subs)
        longbt = "Proceedings of the " + string.Template(longname).substitute(subs)
        fullbt = longbt + " (" + shortbt + ")"

        cshort += [genEntry(id, year, "Proc. " + shortbt)]
        clong += [genEntry(id, year, longbt)]
        cfull += [genEntry(id, year, fullbt)]
        n += 1

def genBparser(records):
    bp = BibTexParser("")
    bp.records = records
    bp.entries_hash = {}
    return bp


for (suffix, records) in [("short", cshort), ("long", clong), ("full", cfull)]:
    #print records
    output = to_bibtex(genBparser(records))
    fname = "confs_%s.bib" % suffix
    f = open(fname, "w")
    f.write("% Autogenerated, do not edit\n")
    f.write(output)
    f.close()
    print "Written %s" % fname
