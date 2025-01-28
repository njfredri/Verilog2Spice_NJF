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

def makeGenerateMethod(cktinfo:dict, wn='45n', wp='45n') -> str:
    final = ''
    title = 'def ' + cktinfo['name'] + '_generate(filename, use_finfet):\n'
    final += title
    final += '\tspice_file = open(filename, "a")\n\n'
    final += '\tspice_file.write("******************************************************************************************\\n")\n'
    final += '\tspice_file.write("*' + cktinfo['name'] + '\\n")\n'
    final += '\tspice_file.write("******************************************************************************************\\n")\n'
    subcktports = ''
    for port in cktinfo['ports']:
        subcktports += port + ' '
    subcktdef = '\tspice_file.write(".SUBCKT ' + cktinfo['name'] + ' ' + subcktports + 'Wn=' + wn +' Wp=' + wp + '\\n")\n'
    final += subcktdef
    for c in cktinfo['components']:
        cs = c['name'] + ' '
        portstr = ''
        for port in c['connections']:
            portstr += port + ' '
        cs += portstr
        cs += c['type'] + ' '
        cs += 'L=gate_length'
        if c['type'] == 'nmos':
            cs += ' W=Wn AS=Wn*trans_diffusion_length AD=Wn*trans_diffusion_length PS=Wn+2*trans_diffusion_length PD=Wn+2*trans_diffusion_length'
        elif c['type'] == 'pmos':
            cs += ' W=Wp AS=Wp*trans_diffusion_length AD=Wp*trans_diffusion_length PS=Wp+2*trans_diffusion_length PD=Wp+2*trans_diffusion_length'
        final+='\tspice_file.write("' + cs + '\\n")\n'
    final += '\tspice_file.write(".ENDS\\n")\n'
    final += '\n\tspice_file.close()'
    return final

def extract_gate_name(gate_string):
    # Regular expression to match the gate name and preserve the number of inputs
    #find last X
    lastX = gate_string.lower().rfind('x')
    match = False
    if lastX != None and lastX > 0:
        match = True

    if match:
        # Extract the gate name and number of inputs
        # gate_name = match.group(1)  # This is the gate's main name (e.g., 'NOR')
        # num_inputs = match.group(2)  # This is the number of inputs (e.g., '2')
        gate_name = gate_string[0:lastX]

        # Return the combined result: main name with the number of inputs
        return gate_name
    else:
        # If the format doesn't match, return None or an error message
        return None

def isItVdd(name:str) -> bool:
    if 'vdd' in name.lower():
        return True
    return False

def isItGnd(name:str) -> bool:
    if 'gnd' in name.lower():
        return True
    if 'ground' in name.lower():
        return True
    return False

def isItVss(name:str) -> bool:
    if 'vss' in name.lower():
        return True
    return False



def correct_vdd_vss(cktinfo:dict, newvdd='VDD', newvss='VSS', gnd_is_Vss=True) -> dict:
    #detect if vdd and vss exist in ports
    vddexist = False
    vdds = []
    vssexist = False
    vsss = []
    for port in cktinfo['ports']:
        if isItVss(port):
            vssexist = True
            vsss.append(port)
        if isItVdd(port):
            vddexist = True
            vdds.append(port)
        if isItGnd(port):
            if gnd_is_Vss:
                vssexist = True
                vsss.append(port)
            else:
                vddexist = True
                vdds.append(port)
    
        

    



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='cdl translation tool',
        description='Converts a cdl to another technology node using information from a spice model',
        epilog='',
    )

    parser.add_argument('-lib', '-cdl ', '--library', required=True)
    # parser.add_argument('-sp', '--spice', required=True)
    parser.add_argument('-out', '--output')
    parser.add_argument('-pmos', '--pmosname')
    parser.add_argument('-nmos', '--nmosname')


    args = parser.parse_args()
    print(args)
    libin = args.library
    # spin = args.spice
    out = args.output
    if out == None:
        out = 'generate.py'
    pmosname = args.pmosname
    if pmosname == None:
        pmosname = 'pmos'

    nmosname = args.nmosname
    if nmosname == None:
        nmosname = 'nmos'

    libf = open(libin)
    # spf = open(spin)

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
    categorizedCircuits = {'misc': []}
    for subckt in newsubinfo:
        added = False
        minInfo = {}
        minInfo['name'] = subckt['name']
        minInfo['ports'] = subckt['ports']
        for gate in basicgates['gates']:
            if gate in subckt['name'].lower():
                if gate in categorizedCircuits.keys():
                    categorizedCircuits[gate].append(minInfo)
                else:
                    categorizedCircuits[gate] = []
                    categorizedCircuits[gate].append(minInfo)
                added = True
        if not added:
            categorizedCircuits['misc'].append(minInfo)

    #use the categorized information to remove redundant gates (any gates that have the same category and ports)
    transmap = {}
    for key in categorizedCircuits.keys():
        if key != 'misc':
            # print('\n\n' + str(key) + '\n')
            sublist = categorizedCircuits[key]
            #create a list of unique ports
            uPort = {}
            for sub in sublist:
                portstr = ''
                for port in sub['ports']:
                    portstr += port.lower() + ' '
                if portstr not in uPort.keys():
                    uPort[portstr] = [sub['name']]
                else:
                    uPort[portstr].append(sub['name'])
            # print(uPort)

            #loop through the uPort and create a mapping of old circuits to new circuits
            for key in uPort.keys():
                name = extract_gate_name(uPort[key][0])
                if name != None:
                    if(name in transmap.keys()): #deal with possible overlaps
                        digit=1
                        # print(name)
                        newname = str(name)+'_'+str(digit)
                        while newname in transmap.keys():
                            digit+=1
                            newname = name+'_'+str(digit)
                        name = newname
                    transmap[name] = uPort[key]
                else:
                    print('got None as name for ' + str(key) + str(uPort[key]))
                    transmap[uPort[key][0]] = [uPort[key]]
        else:
            print('going through misc:\n') #no good way to detect redundancies or lack of with misc circuits
            for sub in categorizedCircuits[key]:
                print(sub)
                transmap[sub['name']] = [sub['name']]

    for key in transmap.keys():
        print(str(key) + ' ' + str(transmap[key]))

    #need to invert the map so that the original names can be used as lookups
    finalmap = {}
    for key in transmap.keys():
        for item in transmap[key]:
            if isinstance(item, list):
                print('item is a list, pls fix: ' +str(item) + ' key: ' + key)
            finalmap[str(item)] = 'njf_' + key

    #now that you have a map, create the map file as a json
    mapfile = open('mapfile.json', 'w+')
    json.dump(finalmap, mapfile)

    #Create minimum collection of subcircuits
    finalSubs = []
    finalNames = []
    for sub in newsubinfo:
        translatedname = finalmap[sub['name']]
        if translatedname in finalNames:
            continue
        else:
            finalNames.append(translatedname)
            newsub = sub
            newsub['name'] = translatedname
            finalSubs.append(newsub)

    #rename vss and vdd
    for sub in finalSubs:
        rename_vss_gnd(sub)
        # print(sub)

    wrapper = {}
    wrapper['subcircuits'] = finalSubs
    with open('temp2.json', 'w+') as outfile:
        json.dump(wrapper, outfile)



    #finally, create the standard library file
    #TODO create a function that will generate a python method as a string
    #The resulting python methods should each generate the subcircuits
    code = ''
    methods_to_call = []
    for sub in finalSubs:
        code += makeGenerateMethod(sub) + '\n'

    output = open(out, 'w+')
    output.write(code)
    output.close