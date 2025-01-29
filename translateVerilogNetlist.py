import json
import re

class translateVerilogNetlist:
    def __init__(self):
        self.inputs = [] #include reg and wires
        self.outputs = []
        self.wires = []
        self.regs = []
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

if __name__ == '__main__':
    # translateVerilogNetlist.minimumVerilog('synthesized_flat.v')
    tvn = translateVerilogNetlist()