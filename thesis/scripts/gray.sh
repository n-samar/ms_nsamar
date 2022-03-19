#!/bin/bash
gs \
	-sOutputFile=$2 \
	-sDEVICE=pdfwrite \
	-sColorConversionStrategy=Gray \
	-dProcessColorModel=/DeviceGray \
	-dOverrideICC \
	-dPDFUseOldCMS=false \
	-dCompatibilityLevel=1.4 \
	-dNOPAUSE \
	-dBATCH \
	$1
