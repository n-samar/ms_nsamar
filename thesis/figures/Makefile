default: moves

figures-crop.pdf: figures.pdf Makefile
	pdfcrop figures.pdf
	#pdfcrop more_figures.pdf

doc_data.txt: figures-crop.pdf
	#pdftk figures-crop.pdf burst output drawing_%02d.pdf
	pdfseparate figures-crop.pdf drawing_%02d.pdf
	#pdfseparate more_figures-crop.pdf more_drawing_%02d.pdf

# Now for some fun Makefile hackery: pdfcrop generates a report, called doc_data.txt. We depend on that report,
# not the drawing_XX.pdf files, so that those files can be deleted. Only clean, not tidy, kills that report 

moves: ag_speedups.pdf

#Need to name this as a file...
ag_speedups.pdf: doc_data.txt
	cp drawing_01.pdf ag_four_step_ntt.pdf
	cp drawing_02.pdf ag_quadrant_swap.pdf
	cp drawing_03.pdf ag_transpose.pdf
	cp drawing_04.pdf ag_automorphism.pdf
	cp drawing_05.pdf ag_overview.pdf
	cp drawing_11.pdf ag_arch.pdf
	cp drawing_07.pdf ag_mult_dataflow.pdf
	#cp drawing_08.pdf ag_compiler_overview.pdf
	cp drawing_09.pdf ag_compiler_overview.pdf
	cp drawing_12.pdf ag_aut_fu.pdf

tidy:
	rm -f drawing_*.pdf

clean: tidy
	rm -f doc_data.txt
	rm -f ag_*.pdf
	rm -f figures-crop.pdf
