'''
Assembler for IKEa
@author Justin Chen
@since 11/22/2023
'''

import argparse
import os
import re

# Declare some static instruction codes
INSTRUCTION_CODES = {
    "ADD": "0000100000000000100000001000000000000000",
    "ADD_SETFLAG": "1000100000000000100000000100000000000000",
    "SUB": "0000100000000000010000000010000000000000",
    "SUB_SETFLAG": "1000100000000000010000000001000000000000",
    "AND": "0000100000000000001000000000100000000000",
    "OR": "0000100000000000000100000000010000000000",
    "LOAD": "0100010000000000100000000000001000000000",
    "STORE": "0101000001000000100000000000000100000000",
    "ADDRESS": "0100100000000000000001000000000000000001",
    "SET": "0000100000000000000001000000000010000000",
    "SET::IMM": "0100100000000000000001000000000001000000",              # Immediate number version of SET
    "BRANCH": "0100000100000000000010000000000000100000",
    "BRANCH_LINK": "0100000100000000000010000000000000010000",
    "BRANCH_IF_ZERO": "0100001000000000000000100000000000001000",
    "BRANCH_IF_NOT_ZERO": "0100001000000000000000100000000000000100",
    "RETURN": "0000000010000000000001000000000000000010"
}

# Seperates instructions in 7 categories. Some of them are redundant (not too optimized)
# but human readability > optimization (software engineering mindset lmao) so we're splitting it into 7

# Category 1 follows WR, RR1, RR2
CAT1 = [
    "ADD", "ADD_SETFLAG", "SUB", "SUB_SETFLAG", "AND", "OR"
]

# Category 2 follows WR, RR1, offset (8 bit imm)
CAT2 = [
    "LOAD"
]

# Category 3 follows WR, label
CAT3 = [
    "ADDRESS"
]

# Category 4 follows RR1, RR2, offset (8 bit imm)
CAT4 = [
    "STORE"
]

# Category 5 follows WR, RR2
CAT5 = [
    "SET"
]

# Category 6 follows WR, 8 bit imm
CAT6 = [
    "SET::IMM"
]

# Category 7 follows [label]
CAT7 = [
    "BRANCH",
    "BRANCH_LINK"
]

# Category 8 follows RR1, label
CAT8 = [
    "BRANCH_IF_ZERO",
    "BRANCH_IF_NOT_ZERO"
]

# Category 9 is just RETURN
CAT9 = [
    "RETURN"
]

def convert_8_bit_bin(item:str) -> str:
    '''
    Converts a given item into 8 bit binary
    If something contains an X (prolly from a register), remove it
    @param item Thing to convert. This MUST be an actual number
    @return Binary form of item
    '''
    num_2_parse = int(item.replace("X", ""))
    return format(num_2_parse,'08b')

def check_file_syntax(fileArr: list[str]):
    '''
    Check the file of instructions to ensure it has a .text and .data segment
    @param fileArr An array of IKEA instructions
    '''
    assert ".text" in fileArr, "IKEA files must have a .text segment to denote IKEA Assembly code"
    assert ".data" in fileArr, "IKEA files must have a .data segment to denote items stored in memory"

def generate_image_files(fileArr:list[str]):
    '''
    Generates two image files given array of instructions (one for .data and one for .text)
    @param fileArr An array of IKEA instructions
    '''

    print(fileArr)
    return

def generate_binary(instruction:str) -> str:
    '''
    Given a string containing IKEA instructions, convert that to binary
    @param instruction The instruction to convert
    @returns Binary codes of the instruction string
    '''
    EIGHT_ZEROES = "00000000"                   # Constant for a byte full of zeroes

    space_idx = instruction.index(" ")          # The index of the space in instructions
    command = instruction[0:space_idx]          # The physical command we want to execute

    # Instruction params are split by semicolons. This is why it was important earlier to get rid of whitespace after ","
    instruction_params = instruction[space_idx + 1:].split(",")     
    instruction_params = list(map(lambda item: convert_8_bit_bin(item), instruction_params))    # Convert this to binary so machine code can use them

    opcode = INSTRUCTION_CODES[command]

    if command in CAT1 or command in CAT2:
        return f"{opcode}{instruction_params[2]}{instruction_params[1]}{instruction_params[0]}"
    elif command in CAT3:
        return          # Implement after the data image is handled
    elif command in CAT4:
        return f"{opcode}{instruction_params[2]}{instruction_params[0]}{instruction_params[1]}"
    elif command in CAT5 or command in CAT6:
        return f"{opcode}{instruction_params[1]}{EIGHT_ZEROES}{instruction_params[0]}"
    elif command in CAT7:
        return
    elif command in CAT8:
        return
    elif command in CAT9:
        return f"{opcode}{convert_8_bit_bin('X30')}{EIGHT_ZEROES}{EIGHT_ZEROES}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Assembles a IKEA file and generates binary codes according to specifications. The file must end in .ikea", 
        usage="$python ikeaAssemble.py [file_path]"
    )

    parser.add_argument('-f', '--file', help='The code file to assemble', required=True)

    flags = vars(parser.parse_args())

    if (not os.path.exists(flags["file"])):
        raise FileNotFoundError("The code file does not exist")
    
    if (os.path.splitext(flags["file"])[1] != ".ikea"):
        raise FileNotFoundError("The file inputted is not a .ikea file")
    
    with open(flags["file"]) as ikea_file:
        # Read and parse the file (and clean it)
        ikea_instructions = ikea_file.read()
        ikea_instructions = ikea_instructions.split("\n")

        # Get rid of everything after '#'
        ikea_instructions = list(map(lambda line: re.sub(r"#.*$", "", line), ikea_instructions))
        ikea_instructions = list(map(lambda line: line.strip(), ikea_instructions))

        # Get rid of all whitespace after commas
        ikea_instructions = list(map(lambda line: re.sub(r",\s", ",", line), ikea_instructions))
        
        # Filter blank rows
        ikea_instructions = list(filter(lambda line: line != "", ikea_instructions))

        check_file_syntax(ikea_instructions)
        generate_image_files(ikea_instructions)
        #generate_binary(ikea_instructions[4])
        print(convert_8_bit_bin("X8"))