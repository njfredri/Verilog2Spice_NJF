#! usr/bin/python

#   Script to convert .cdl cell libraries into another technology node
#   Ex. SAED90nm.cdl -> ptm_22nm.l
#   Input is .cdl and output is .l
#   Some information such as metal layers will be removed
##############################################################################

import argparse
import re

def extractCellNames(input: str) -> str:
    # Regular expression to extract cell names
    matches = re.findall(r'\* Cell\s*:\s*(\S+)', input)
    
    names = []

    #go through matches and remove .SCH and ;
    for match in matches:
        match = match.replace('.SCH','')
        match = match.replace('.sch','')
        match = re.sub(r";\d*", '', match)
        names.append(match)

    # Print all cell names found
    # print("Extracted cell names:", names)
    finalstr = '**************Cell Library**************\n'
    for name in names:
        finalstr += '*CellName: ' + name + '\n'
    finalstr += '***********************************************\n'
    return finalstr

def cleanCdl(file) -> str:
    cleanlines = []
    emptylines = ['\n', ' ', '\t']
    for line in file:
        #remove all content after *
        #one exception being Cell labels
        linesplit = line.split('*')
        cleanline = linesplit[0]
        if len(linesplit) > 1:
            if 'cell' in str.lower(linesplit[1]):
                cleanline += '\n*' + linesplit[1]
        #remove metal layer
        cleanline = re.sub(r"m=\d+", "", cleanline)
        cleanline = re.sub(r"m = \d+", "", cleanline)
        #remove extra spaces
        cleanline = re.sub(r"\s+", " ", cleanline).strip()


        if len(cleanline) != 0 and cleanline not in emptylines:
            cleanlines.append(cleanline)
    finalstr = ''
    for line in cleanlines:
        finalstr += line + '\n'
    return finalstr

def reformatLib(lib: str) -> str:
    #add newlines before commented lines
    lib = re.sub(r"\* *cell", "\n\n* Cell", lib, flags=re.IGNORECASE)
    #add newline before .subckt
    lib = lib.replace(".subckt", "\n.subckt")
    #add newline before .global
    lib = lib.replace(".global", "\n.global")
    return lib

def extractSUBCKTInfo(ckt:str) -> dict:
    print(ckt)
    cktlines = ckt.split('\n')
    topdef = cktlines[0]
    

parser = argparse.ArgumentParser(
    prog='cdl translation tool',
    description='Converts a cdl to another technology node using information from a spice model',
    epilog='',
)

parser.add_argument('-lib', '-cdl ', '--library', required=True)
parser.add_argument('-sp', '--spice', required=True)
parser.add_argument('-out', '--output')

args = parser.parse_args()
print(args)
libin = args.library
spin = args.spice
out = args.output
if out == None:
    out = 'output.l'

libf = open(libin)
spf = open(spin)

lintedlib = cleanCdl(libf)
reformatted= reformatLib(lintedlib)
cellnames = extractCellNames(reformatted)
# reformatted = cellnames + '\n' + reformatted

#now go through and extract information for each
subckts = lintedlib.split('.subckt')
# print(subckts)
extractSUBCKTInfo(subckts[1])
extractSUBCKTInfo(subckts[5])


outf = open(out, mode='+w')
outf.write(reformatted)