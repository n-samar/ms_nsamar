#!/bin/bash
# Special-purposed for the abstract... pass this thru detex for more generality? 
cat $1 | grep -v "^\%" | sed "s/\\\\name/SCC/g" | sed "s/\\\\%/%/g" | sed "s/\\\\times/x/g" | sed "s/\\$//g" | sed "s/\\\\hyp{}/-/g" | sed "s/\\\\emph{//g" | sed "s/}//g" | tr -s ' ' | sed ':a;N;$!ba;s/\n/ /g' | sed "s/  /\n\n/g" | sed "s/\\\\acs{//g"
