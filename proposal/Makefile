PAPER_NAME=ms_proposal
# Halt on errors instead of going to the shell
LATEX_OPTS=-halt-on-error -mode=batch

default: web

figs:
#	make -C figures/
#	make -C plots/

fast: figs Makefile
	pdflatex $(LATEX_OPTS) $(PAPER_NAME)

paper: figs Makefile
	date > auto_header.tex
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

web: paper
	yes | cp $(PAPER_NAME).pdf ~/public_html/

tidy: Makefile
	rubber --clean $(PAPER_NAME)
	rm -f auto_header.tex

warn: paper
	pdflatex $(PAPER_NAME).tex 2>&1 | grep Warning
	#rubber -W all $(PAPER_NAME).tex

clean: tidy
	rm -f $(PAPER_NAME).pdf $(PAPER_NAME)_opt.pdf $(PAPER_NAME)_opt2.pdf rubber.cache
	rm -f scripts/*.pyc
