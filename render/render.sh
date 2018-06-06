#!/bin/bash

#
# Make sure there is an argument
#
if [ -z $1 ] ; then
    echo "Usage: $0 path/to/file.txt|.org"
    exit 1
fi

#
# Determine if we are running in Docker or not
#
IN_DOCKER=0
if [ -f /proc/1/cgroup ] ; then
    docker_lines=`grep docker /proc/1/cgroup | wc -l`
    if [ $docker_lines > 0 ] ; then
        IN_DOCKER=1
    fi
fi
BASENAME=`dirname $0`
EXPORT_ELISP=${BASENAME}/export.el
EXPORT_CMD='(org-latex-export-to-latex)'
#
# If we are running in Docker, set the directory to /source
#
if [ $IN_DOCKER -eq 0 ] ; then
    SOURCE_DIR=`dirname $1`
else
    SOURCE_DIR=/source
    EXPORT_ELISP=/export.el
fi
SOURCE_FILE=`basename $1`
OUTPUT_FILE=${SOURCE_FILE%.*}
#
# Set the working directory for where the .txt file is
#
cd $SOURCE_DIR
#
# use a headless Emacs to convert the org-mode file to a LaTeX file
#
echo "Exporting..."
emacs --batch --no-site-file --load $EXPORT_ELISP --visit $1 --eval $EXPORT_CMD
#
# Run the many copies of pdflatex with a makeindex in the middle to resolve all
# of the references (single-pass compilers ftw!)
#
echo "Compiling..."
pdflatex -shell-escape -halt-on-error $OUTPUT_FILE > /dev/null 2>&1 || exit 1
pdflatex -shell-escape -halt-on-error $OUTPUT_FILE > /dev/null 2>&1 || exit 1
pdflatex -shell-escape -halt-on-error $OUTPUT_FILE > /dev/null 2>&1 || exit 1
echo "Indexing..."
makeindex $OUTPUT_FILE > /dev/null 2>&1
echo "Compiling..."
pdflatex -shell-escape -halt-on-error $OUTPUT_FILE > /dev/null 2>&1 || exit 1
pdflatex -shell-escape -halt-on-error $OUTPUT_FILE > /dev/null 2>&1 || exit 1
#
# delete a bunch of LaTeX output files
#
echo "Cleaning up..."
/bin/rm -r _minted-$OUTPUT_FILE $OUTPUT_FILE.aux $OUTPUT_FILE.idx $OUTPUT_FILE.ilg $OUTPUT_FILE.ind $OUTPUT_FILE.log $OUTPUT_FILE.out $OUTPUT_FILE.toc $OUTPUT_FILE.tex
echo "Output is in ${OUTPUT_FILE}.pdf"
