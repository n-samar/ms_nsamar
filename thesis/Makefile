PAPER_NAME=ms_thesis
CAMERA_NAME=$(PAPER_NAME)
# Halt on errors instead of going to the shell
LATEX_OPTS=-halt-on-error -mode=batch
BIB = refs.bib confs.bib

default: paper

figs:
	make -C figures/

fast: figs Makefile
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)

paper: figs Makefile $(BIB)
	date > auto_header.tex
	echo "--- rev" >> auto_header.tex
	python scripts/gitver.py >> auto_header.tex
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)
	bibtex -min-crossrefs=30000 $(PAPER_NAME)
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)
	ps2pdf -dPDFSETTINGS=/prepress -dCompatibilityLevel=1.4 -dEmbedAllFonts=true -dSubsetFonts=true -r600 $(PAPER_NAME).pdf $(PAPER_NAME)_opt.pdf
	# Preserve metadata
	pdftk $(PAPER_NAME).pdf dump_data output metadata.txt
	pdftk $(PAPER_NAME)_opt.pdf update_info metadata.txt output $(PAPER_NAME)_opt2.pdf
	qpdf --linearize $(PAPER_NAME)_opt2.pdf $(PAPER_NAME).pdf


tidy: Makefile
	rubber --clean $(PAPER_NAME)
	rm -f auto_header.tex

warn: paper
	pdflatex $(PAPER_NAME).tex 2>&1 | grep Warning
	#rubber -W all $(PAPER_NAME).tex

clean: tidy
	make -C figures/ clean
	make -C plots/ clean
	rm -f $(PAPER_NAME).pdf $(PAPER_NAME)_opt.pdf $(PAPER_NAME)_opt2.pdf rubber.cache
	rm -f scripts/*.pyc

web: paper
	cp $(PAPER_NAME).pdf ~/public_html/private/manuscripts/
