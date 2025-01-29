import json
import re

class translateVerilogNetlist:
    def __init__(self):
        self.inputs = [] #include reg and wires
        self.outputs = []
        self.wires = []
        self.regs = []
        self.portTranslations = {}
        minV = translateVerilogNetlist.minimumVerilogLines('synthesized_flat.v')
        minLines = translateVerilogNetlist.joinLines(minV)
        self.verilogLines = minLines
        self.inputs = translateVerilogNetlist.grabSignals(self.verilogLines, 'input')
        self.outputs = translateVerilogNetlist.grabSignals(self.verilogLines, 'output')
        self.wires = translateVerilogNetlist.grabSignals(self.verilogLines, 'wire')
        self.regs = translateVerilogNetlist.grabSignals(self.verilogLines, 'reg')
        # print(self.inputs)
        # print(self.outputs)
        # print(self.wires)
        # print(self.regs)
        self.celltranslation = json.load(open('circuit_translation.json'))
        self.cellInfo = json.load(open('subcircuit_info.json'))
        self.cellNames = []
        for cell in self.cellInfo['subcircuits']:
            self.cellNames.append(cell['name'])
        self.extractPortTranslation()
        self.replaceCells()
        self.replacePorts()
        for line in self.verilogLines:
            print(line)
        # for key in self.portTranslations:
        #     print(key + ' ' + str(self.portTranslations[key]))

    def clean_whitespace(text):
        return re.sub(r'\s+', ' ', text).strip()

    def minimumVerilogLines(verilogFile:str) -> list:
        vfile = open(verilogFile, 'r')
        minlines = []
        for line in vfile.readlines():
            cleanedline = translateVerilogNetlist.clean_whitespace(line)
            if '//' in cleanedline: #remove comments
                cleanedline = cleanedline.split('//')[0] 
            if(len(cleanedline) > 0):
                # print(cleanedline)
                minlines.append(cleanedline)
        return minlines

    def joinLines(lines, ends=[';', 'endmodule', 'begin']): #join multi-line statements
        result = []
        buffer = ""
        for line in lines:
            line = line.strip() #double check there are no whitespaces at the end
            if buffer:
                bufferEndsSuffix = False
                for end in ends: #check if buffer ends with one of the ends
                    if buffer.endswith(end):
                        bufferEndsSuffix = True
                        break
                #if it does, just add it to the result as a line
                if bufferEndsSuffix:
                    result.append(buffer)
                    buffer = line #start new buffer with current line
                else:
                    buffer += ' ' + line #append current line to end of buffer
            else:
                buffer = line
        #add last line
        if buffer:
            result.append(buffer)

        return result

    def grabSignals(lines, type:str):
        names = []
        for line in lines:
            if line.startswith(type):
                #remove ; [:]
                typelessline = str(line).replace(type, '')
                typelessline = typelessline.replace(';', '')
                typelessline = re.sub(r'\[\d+:\d+\]', '', typelessline) #removes [number:number]
                #loop through everything separated by commas
                for name in typelessline.split(','):
                    names.append(name.strip())
        return names

    def replaceCells(self):
        result = []
        for line in self.verilogLines:
            #see if line begins with a cell name
            split = line.split(' ')
            beginning = split[0].strip()
            rest = ' '.join(split[1:])
            if beginning in self.celltranslation.keys():
                newline = self.celltranslation[beginning] + ' ' + rest
                result.append(newline)
            else:
                result.append(line)
        self.verilogLines = result

    def extractPortTranslation(self):
        self.portTranslations = {}
        for sub in self.cellInfo['subcircuits']:
            #if ports stayed the same, then skip making a translation dictionary
            if sub['ports_changed'] == False:
                continue

            else: #otherwise make a map
                name = sub['name']
                translation = {} #original name : new name
                oldports = sub['old_ports']
                newports = sub['ports']

                #grab vdd, vss translation
                vtrans = sub['vddvss_translation']
                for op in oldports:
                    if op in sub['unused_ports']:
                        #no translation will be added, as the port will not be kept
                        continue
                    elif op in sub['ports']: #if in new ports, then translate it to itself
                        translation[op] = op
                    else: #check if in the vddvss translation somewhere
                        for key in vtrans.keys():
                            if op in vtrans[key]: #if it is in the list, then add the key (vss or vdd) as translation
                                translation[op] = key
                #now add the translation. Form =  circuitname : translation_dictionary
                self.portTranslations[name] = translation
        for key in self.portTranslations:
            print(key)
            print(self.portTranslations[key])
                            
    def replacePorts(self):
        newlines = []
        portPattern = r'\.(\w+)\(([^)]+)\)'
        for line in self.verilogLines:
            split = line.split(' ')
            type = split[0].strip()
            if type in self.cellNames and len(split) > 1:
                if type in self.portTranslations.keys():
                    #get name
                    name = split[1]
                    #if its an instance of a shell, go ahead
                    port_matches = re.findall(portPattern, line)
                    port_dict = {port: connection for port, connection in port_matches}
                    
                    #go through and replace the ports
                    newports = {}
                    for key in port_dict.keys():
                        #check if there is a translation. If not, it is an unused port to be removed
                        if key in self.portTranslations[type].keys():
                            newportname = self.portTranslations[type][key]
                            newports[newportname] = port_dict[key]
                    print('translated ' + type + ' ports from ' + str(port_dict) + ' to ' + str(newports))

                    newline = type + ' ' + name + ' ( '
                    first = True
                    for port in newports.keys():
                        if not first:
                            newline += ', '
                        else:
                            first = False
                        newline += '.' + port + '(' + newports[port] + ')'
                    newline += ' );'
                    newlines.append(newline) 
                else:
                    newlines.append(line)
            else:#no translation map. therefore, keep it the same
                newlines.append(line)
        self.verilogLines = newlines
        return

if __name__ == '__main__':
    # translateVerilogNetlist.minimumVerilog('synthesized_flat.v')
    tvn = translateVerilogNetlist()