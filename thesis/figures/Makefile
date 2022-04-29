default: figures-crop.pdf doc_data.txt
	cp drawing_01.pdf ag_placeholder.pdf
	cp drawing_02.pdf ag_overview.pdf
	cp drawing_03.pdf ag_crb.pdf
	cp drawing_04.pdf ag_tiling.pdf
	cp drawing_05.pdf ag_workflow.pdf
	cp drawing_06.pdf ag_newKS.pdf
	cp drawing_07.pdf ag_interClusterTiling.pdf
	cp drawing_08.pdf ag_pipeline.pdf
	cp drawing_09.pdf ag_bootstrapping.pdf
	cp drawing_10.pdf ag_tilingExample.pdf
	cp drawing_28.pdf ag_bootstrappingFrequency.pdf

figures-crop.pdf: figures.pdf Makefile
	pdfcrop figures.pdf

doc_data.txt: figures-crop.pdf
	pdfseparate figures-crop.pdf drawing_%02d.pdf

# Now for some fun Makefile hackery: pdfcrop generates a report, called doc_data.txt. We depend on that report,
# not the drawing_XX.pdf files, so that those files can be deleted. Only clean, not tidy, kills that report

tidy:
	rm -f drawing_*.pdf

clean: tidy
	rm -f doc_data.txt
	rm -f ag_*.pdf
	rm -f figures-crop.pdf
