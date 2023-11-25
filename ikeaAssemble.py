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

# ---------------------- HELPER FUNCTIONS ------------------------------
def convert_8_bit_bin(item:str) -> str:
    '''
    Converts a given item into signed 8 bit binary
    If something contains an X (prolly from a register), remove it
    @param item Thing to convert. This MUST be an actual number
    @returns Binary form of item
    '''
    num_2_parse = int(item.replace("X", ""))

    if num_2_parse < 0:                 # Use twos complement. -1 is really MAX_NUM - 1 in signed
        num_2_parse += 2 ** 8
    
    return format(num_2_parse,'08b')

def convert_nibble_hex(item:str) -> str:
    '''
    Converts a nibble (4 bits) into hex
    @param item Thing to convert. This MUST be an actual number
    @returns Hexadecimal form of item
    '''
    num_2_parse = int(item.replace("X", ""))
    assert num_2_parse < 16 and num_2_parse >= 0, "The number must be a positive integer that can fit within 4 bytes"
    return format(num_2_parse,'x')

def convert_8_byte_hex(item:str) -> str:
    '''
    Converts a given item into a signed 8 byte hexadecimal.
    If something contains an X, remove it.
    @param item Thing to convert. This MUST be a parsable number
    @returns Hexadecimal form of item
    '''
    num_2_parse = int(item.replace("X", ""))

    if num_2_parse < 0:                 # Use twos complement. -1 is really MAX_NUM - 1 in signed
        num_2_parse += 2 ** 64

    return format(num_2_parse,'016x')

def convert_1_byte_hex(item:str) -> str:
    '''
    Converts 1 byte (8 bits) into hex
    @param item Thing to convert. This MUST be an actual number
    @returns Hexadecimal form of item
    '''
    num_2_parse = int(item.replace("X", ""))

    if num_2_parse < 0:                 # Use twos complement. -1 is really MAX_NUM - 1 in signed
        num_2_parse += 2 ** 8
    
    return format(num_2_parse,'02x')

def check_file_syntax(fileArr: list[str]):
    '''
    Check the file of instructions to ensure it has a .text and .data segment
    @param fileArr An array of IKEA instructions
    '''
    assert ".text" in fileArr, "IKEA files must have a .text segment to denote IKEA Assembly code"
    assert ".data" in fileArr, "IKEA files must have a .data segment to denote items stored in memory"

class RAMROM_dict:
    def __init__(self):
        '''
        Generates a 256 byte representation of RAM and ROM memory in dictionary form
        This class resembles an image file that we will write to.
        '''

        '''
        The image file, represented as a dictionary.
        The keys in the dict are placed at 16 bit intervals (represented in hex) and values being array of len 16
        It's structured this way as LOGISIM image files are structured in a similar fashion
        '''
        self.image_file = {
            "00": ["00"] * 16,
            "10": ["00"] * 16,              # These look like increments of 10, but they're in hex so they're actually increments of 16
            "20": ["00"] * 16,
            "30": ["00"] * 16,
            "40": ["00"] * 16,
            "50": ["00"] * 16,
            "60": ["00"] * 16,
            "70": ["00"] * 16,
            "80": ["00"] * 16,
            "90": ["00"] * 16,
            "a0": ["00"] * 16,
            "b0": ["00"] * 16,
            "c0": ["00"] * 16,
            "d0": ["00"] * 16,
            "e0": ["00"] * 16,
            "f0": ["00"] * 16
        }
        
        # This is more of a helper variable that simplifies implementation down the line. It's a bit excessive to declare another one here,
        # but I value readability > optimization in my code so here we go
        self.keys = list(self.image_file.keys())

        '''
        Pointer to the current location inside the image file that we should write to
        The first item in that tuple represents the key to write to. The second item represents the index to write to
        '''
        self.current_loc = ("00", 0)

    def __update_current_loc(self, byte_size:int=8):
        '''
        Updates the current location tracker for the RAM/ROM dict by $byte_size. By default, this is 8 bytes.
        @precondition byte_size is a power of 2 (2 ** 0 to 2 ** 4)
        @param byte_size The byte size to update current location pointer by
        @raises MemoryError Due to RAM/ROM's memory limit, the compiler will throw a memory exception if you try to update current location when you're at ("f0", 16 - $byte_size)
        '''
        # Constant that represents the last idx you can store something in a row before having to move on to the next index
        MAX_BYTE_IN_ROW = 16 - byte_size    

        if self.current_loc == ("f0", 16 - byte_size):
            raise MemoryError("Too many instructions or data being declared. IKEA only handles up to 256 bytes of data.")

        current_key, current_idx = self.current_loc

        if current_idx != MAX_BYTE_IN_ROW:
            current_idx += byte_size                 # If current index is not at max_byte yet, we add $byte_size to get the next location (since memory files are in increments of 16)
        else:
            # Otherwise, set the current index to 0 and move the current key to the next key
            current_idx = 0

            # This will never go out of bounds -- ("f0", 16 - $byte_size) throws a MemoryError and is already caught
            current_key = self.keys[self.keys.index(current_key) + 1]

        self.current_loc = (current_key, current_idx)

    def write_bytes(self, to_write:str, byte_size:int=8) -> str:
        '''
        Writes $byte_size bytes to the RAM/ROM dict. By default, this writes 8 bytes
        LSB goes to lower addresses (and vice versa for MSB)
        @param to_write The string of data (in hexadecimal form) to write
        @param byte_size Number of bytes to write
        @returns A string representing the address the current item is in (in 8 bit binary)
        '''
        HEX_IN_BYTE = 2
        assert len(to_write) == byte_size * HEX_IN_BYTE, f"to_write is not {byte_size} bytes (needs {byte_size * HEX_IN_BYTE} hexadecimals)"

        current_key, current_idx = self.current_loc

        # byte_size - 1 because indexing is dumb
        # The second argument in range is -1 because we want to take into account 0
        for i in range(byte_size - 1, -1, -1):
            self.image_file[current_key][current_idx + i] = to_write[HEX_IN_BYTE * i : HEX_IN_BYTE * i + HEX_IN_BYTE]

        memory_address = f"{current_key[0]}{convert_nibble_hex(str(current_idx))}"

        self.__update_current_loc(byte_size)

        # Returns the address as a binary. It is currently in hex
        return format(int(memory_address, 16), '08b')
    
    def mem_addr_preview(self, instruction_num:int) -> str:
        '''
        This is used to "pre-scan" the file for label locations. This only works for ROM.
        Given the instruction number (ie. 5th instruction), this takes advantage of the fact that each instruction is 8 bytes and predicts the address the instruction will be on
        @param instruction_num The instruction number. Remember you start counting at ZERO
        @returns A string representing the potential ROM address, as an 8 bit binary
        '''
        instruction_idx = instruction_num * 8
        return convert_8_bit_bin(str(instruction_idx))
    
    def generate_image_file(self, file_path:str):
        '''
        Generates an image file for the IKEA Assemble
        @param file_path The file path to write file to
        '''
        to_write = "v3.0 hex words addressed\n"

        for key, value in self.image_file.items():
            to_write += f"{key}:"

            for hexadecimal in value:
                to_write += f" {hexadecimal}"

            to_write += "\n"
                
        with open(file_path, "w") as write_file:
            write_file.write(to_write)

def generate_label_lookup(instructions:list[str], rom_dict:RAMROM_dict) -> dict:
    '''
    IKEA Assembly language preprocessing before we convert
    We will first scan the IKEA file for any labels and try to approximately predict their memory locations
    @param instructions A list of instructions
    @param rom_dict The ROM dictionary "image file" to represent how the instructions will be stored later
    @returns A dictionary<label, predicted memory address in 8 bit binary)
    '''
    label_lookup = dict()
    label_regexp = re.compile(r"^\w+:")

    for i in range(len(instructions)):
        current_instruction = instructions[i]
        re_search_result = label_regexp.search(current_instruction)

        # If there is a match, add its predicted memory slot to the dictionary
        if re_search_result:
            label_lookup[re_search_result.group()] = rom_dict.mem_addr_preview(i)
    
    return label_lookup

# ---------------------- MAIN PROCESSING FUNCTIONS ----------------------------
def generate_image_files(fileArr:list[str], ram_file_path:str, rom_file_path:str):
    '''
    Generates two image files given array of instructions (one for .data and one for .text)
    @param fileArr An array of IKEA instructions
    @param ram_file_path Path to create a image file for memory data
    @param rom_file_path Path to create a image file for instruction binaries
    '''
    instructions = fileArr[fileArr.index(".text") + 1: fileArr.index(".data")]
    memory_data = fileArr[fileArr.index(".data") + 1:]

    # Step 1) Generate RAM/ROM

    # Used to store instructions
    rom = RAMROM_dict()

    # Used to store memory
    ram = RAMROM_dict()

    # Step 2) Take care of memory
    memory_lookup = dict()
    for current_mem_instruction in memory_data:
        generate_memory(ram, memory_lookup, current_mem_instruction)

    # Step 3) Take care of instructions

    label_lookup = generate_label_lookup(instructions, rom)
    for instruction in instructions:
        generate_binary(rom, label_lookup, instruction)

    # Step 4) Generate the two image files
    ram.generate_image_file(ram_file_path)
    rom.generate_image_file(rom_file_path)

def generate_memory(memory_dict:RAMROM_dict, memory_lookup:dict, current_mem_instruction:str):
    '''
    Given a memory instruction (ie. donut: 14), append it to the memory dictionary. This also updates the lookup table so .text image files know how to access items in data
    This assumes that we use the LOGISIM architecture we currently have (instructions go in ROM, memory goes in RAM, and they both start at address 0x0)
    @param memory_dict A RAM/ROM dict (should have been generated via generate_RAMROM_dict function) that will get appended to with the memory
    @param memory_lookup A dictionary<label, address (of LSB)> that holds all the memory of the .data segment
    @param current_mem_instruction The current memory instruction to encode in binary
    '''
    idx_colon = current_mem_instruction.index(":")
    label = current_mem_instruction[0:idx_colon]
    storage = current_mem_instruction[idx_colon + 1:]
    storage_hex = convert_1_byte_hex(storage)

    # First, we alter the memory dictionary. The write function also returns the memory address
    mem_addr = memory_dict.write_bytes(storage_hex, 1)

    # Then, we update the lookup table (RAM)
    memory_lookup[label] = mem_addr
    
def generate_binary(instruction_dict:RAMROM_dict, label_lookup:dict, instruction:str) -> str:
    '''
    Given a string containing IKEA instructions, convert that to binary
    This will write to the lookup table (ROM)
    @param instruction_dict The "image file" to write binary instructions to
    @param label_lookup Dictionary of labels (and their addresses) that we already preprocessed so we can use them later
    @param instruction The instruction to convert
    @returns Binary codes of the instruction string
    '''
    EIGHT_ZEROES = "00000000"                   # Constant for a byte full of zeroes

    space_idx = instruction.index(" ")          # The index of the space in instructions
    command = instruction[0:space_idx]          # The physical command we want to execute
    command = re.sub(r"^\w+:", "", command)    # We have no more uses for labels at this stage since they've already been preprocessed in the lookup table. Remove them.

    # Instruction params are split by semicolons. This is why it was important earlier to get rid of whitespace after ","
    instruction_params = instruction[space_idx + 1:].split(",")

    # If possible, convert the parameters to binary so machine code can use them. We'll take care of edge cases later
    for i in range(len(instruction_params)):    
        if isinstance(instruction_params[i], int):
            instruction_params[i] = convert_8_bit_bin(instruction_dict[i])

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

# ------------------------- PARSE INPUTS --------------------------
def merge_labels(instructions:list[str]) -> list[str]:
    '''
    Creates a new array of instructions where labels are merged with subsequent instructions.
    For instance, ["_amogus:", "ADD X5,X3,X2"] --> ["_amogus:ADD X5,X3,X2"]
    @param instructions Old, unmerged instructions
    @returns A list of new instructions
    '''
    new_instructions = []
    
    # Tracker variable to track whether the last index had a label
    last_idx_label = False

    # Loop through old instructions
    for i in range(len(instructions)):
        if last_idx_label:
            # If the last idx was a label, merge it
            new_instructions.append(f"{instructions[i - 1]}{instructions[i]}")
            last_idx_label = False
        elif re.search(r"^\w+:$", instructions[i]):
            # If the current idx is a label, update the instructions and continue
            last_idx_label = True
            continue
        else:
            # Otherwise, chuck as normal
            new_instructions.append(instructions[i])

    return new_instructions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Assembles a IKEA file and generates binary codes according to specifications. The file must end in .ikea", 
        usage="$python ikeaAssemble.py -f [file_path] -a [Write path for .data] -o [Write path for .text]"
    )

    parser.add_argument('-f', '--file', help='The code file to assemble', required=True)
    parser.add_argument('-a', '--ram', help='Write path for .data image file', required=True)
    parser.add_argument('-o', '--rom', help='Write path for .text image file', required=True)

    flags = vars(parser.parse_args())

    if (not os.path.exists(flags["file"])):
        raise FileNotFoundError("The code file does not exist")
    
    if (os.path.splitext(flags["file"])[1] != ".ikea"):
        raise FileNotFoundError("The file inputted is not a .ikea file")
    
    with open(flags["file"], "r") as ikea_file:
        # Read and parse the file (and clean it)
        ikea_instructions = ikea_file.read()
        ikea_instructions = ikea_instructions.split("\n")

        # Get rid of everything after '#'
        ikea_instructions = list(map(lambda line: re.sub(r"#.*$", "", line), ikea_instructions))
        ikea_instructions = list(map(lambda line: line.strip(), ikea_instructions))

        # Get rid of all whitespace after commas and colons
        ikea_instructions = list(map(lambda line: re.sub(r",\s*", ",", line), ikea_instructions))
        ikea_instructions = list(map(lambda line: re.sub(r":\s*", ":", line), ikea_instructions))
        
        # Filter blank rows
        ikea_instructions = list(filter(lambda line: line != "", ikea_instructions))

        # Clean the labels - if a previous index contains a label, merge it with the subsequent index
        ikea_instructions = merge_labels(ikea_instructions)

        check_file_syntax(ikea_instructions)
        #print(convert_1_byte_hex("64"))
        generate_image_files(ikea_instructions, flags["ram"], flags["rom"])