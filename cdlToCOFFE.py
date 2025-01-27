#! usr/bin/python

#   Script to convert .cdl cell libraries into another technology node
#   Ex. SAED90nm.cdl -> ptm_22nm.l
#   Input is .cdl and output is .l
#   Some information such as metal layers will be removed
##############################################################################

import argparse
import re
import json

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
        cleanline = cleanline.replace(' = ', '=')

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

def filterListForEmptyStr(in_list: list) -> list:
    out_list = []
    for item in in_list:
        if len(item) == 0:
            continue
        if item == ' ':
            continue
        if item == '\n':
            continue
        out_list.append(item)
    return out_list

def extractConnections(splitline: list) -> list:
    out_list = []
    for p in splitline[1:5]:
        if '=' in p:
            continue
        out_list.append(p)
    return out_list

def extractSUBCKTInfo(ckt:str) -> dict:
    info = {}
    # print(ckt)
    cktlines = ckt.split('\n')
    topdef = filterListForEmptyStr(cktlines[0].split(' '))
    # print(topdef)
    info['name'] = topdef[0]
    info['ports'] = topdef[1:]
    info['components'] = []
    for component in cktlines[1:]: #for now, assume everything is nmos and pmos
        cinfo = {}
        split = component.split(' ')
        print('split ' + str(split))
        #skip if end definition
        if(split[0] == '.ends'):
            break

        #figure out how many non-equal things there are
        firstequal = 0
        for spl in split:
            if '=' in spl:
                break
            firstequal += 1
        # print('first equal ' + str(firstequal))
        cinfo['name'] = split[0]
        cinfo['connections'] = split[1:firstequal-1]
        cinfo['type'] = split[firstequal-1]
        cinfo['misc'] = []
        for spl in split[firstequal:]:
            if('l=' in str.lower(spl)):
                cinfo['l'] = spl.split('=')[-1]
            elif('w=' in str.lower(spl)):
                cinfo['w'] = spl.split('=')[-1]
            else:
                cinfo['misc'].append(spl)
        info['components'].append(cinfo)
    return info

def replaceNmosPmos(cktinfo:dict, pmosname:str, nmosname:str) -> dict:
    for comp in cktinfo['components']:
        if comp['type'].lower() == pmosname.lower():
            comp['type'] = 'pmos'
        elif comp['type'].lower() == nmosname.lower():
            comp['type'] = 'nmos'
    return cktinfo

parser = argparse.ArgumentParser(
    prog='cdl translation tool',
    description='Converts a cdl to another technology node using information from a spice model',
    epilog='',
)

parser.add_argument('-lib', '-cdl ', '--library', required=True)
parser.add_argument('-sp', '--spice', required=True)
parser.add_argument('-out', '--output')
parser.add_argument('-pmos', '--pmosname')
parser.add_argument('-nmos', '--nmosname')


args = parser.parse_args()
print(args)
libin = args.library
spin = args.spice
out = args.output
if out == None:
    out = 'output.l'
pmosname = args.pmosname
if pmosname == None:
    pmosname = 'pmos'

nmosname = args.nmosname
if nmosname == None:
    nmosname = 'nmos'

libf = open(libin)
spf = open(spin)

lintedlib = cleanCdl(libf)
reformatted= reformatLib(lintedlib)
cellnames = extractCellNames(reformatted)

#now go through and extract information for each subckt
subckts = lintedlib.split('.subckt')

subinfo = []
for subckt in subckts[1:]:
    subinfo.append(extractSUBCKTInfo(subckt))

wrapper = {}
wrapper['subcircuits'] = subinfo
with open('temp1.json', 'w+') as outfile:
    json.dump(wrapper, outfile)

#go through and replace pmos and nmos names
newsubinfo = []
for subckt in subinfo:
    newinfo = replaceNmosPmos(subckt, pmosname=pmosname, nmosname=nmosname)
    newsubinfo.append(newinfo)

#go through the various gates and categorize them
gatefile = open('basic_circuits.json')
basicgates = json.load(gatefile)
for subckt in newsubinfo:
    for gate in gatefile

wrapper = {}
wrapper['subcircuits'] = newsubinfo
with open('temp2.json', 'w+') as outfile:
    json.dump(wrapper, outfile)

outf = open(out, mode='+w')
outf.write(reformatted)