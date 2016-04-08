#!/bin/bash

GRAMMAR=impera.g
LINE=$(grep -n -e "language=Python3;" < $GRAMMAR  | cut -f 1 -d ':')

sed -i "$LINE s/\/\/\(.*\)/\1/g" $GRAMMAR
java -cp ../../../bin/antlr-3.5.2-complete.jar org.antlr.Tool $GRAMMAR
sed -i "$LINE s/.*/\/\/&/g" $GRAMMAR

sed -i '1i\
# @PydevCodeAnalysisIgnore' impera*.py 
