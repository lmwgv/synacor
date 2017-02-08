import sys
import struct
import logging
import types
import curses
import pickle

registers = [0 for x in range(8)]
stack = []
memory = []
instruction_set = {}

mainwin = None
regwin = None
stackwin = None
asmwin = None

debug_mode = False

def read_data(value):
    if value <= 0x7FFF:
        return value
    return registers[value - 0x8000]


def write_data(destination, value):
    if destination <= 0x7FFF:
        logging.error('Invalid register number')
        sys.exit(0)
    registers[destination - 0x8000] = value % 0x8000


class Instruction():
    def __init__(self, opcode, length, run, window):
        self.opcode = opcode
        self.length = length
        self.run = types.MethodType(run, self)
        self.mnemonic = self.run.__name__[1:]
        self.window = window

    def string(self, program, pc):
        rtn = self.mnemonic + ' '
        rtn += ', '.join((str(program[pc + x]) if program[pc + x] <= 0x7FFF else 'R%d' % (program[pc + x] - 0x8000) for x in range(1, self.length + 1)))
        return rtn


def _halt(self, program, pc):
    return -1


def _set(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]))
    return pc + 3


def _push(self, program, pc):
    stack.append(read_data(program[pc + 1]))
    return pc + 2


def _pop(self, program, pc):
    write_data(program[pc + 1], stack.pop())
    return pc + 2


def _eq(self, program, pc):
    write_data(program[pc + 1], 1 if read_data(program[pc + 2]) == read_data(program[pc + 3]) else 0)
    return pc + 4


def _gt(self, program, pc):
    write_data(program[pc + 1], 1 if read_data(program[pc + 2]) > read_data(program[pc + 3]) else 0)
    return pc + 4


def _jmp(self, program, pc):
    return read_data(program[pc + 1])


def _jnz(self, program, pc):
    return read_data(program[pc + 2]) if read_data(program[pc + 1]) != 0 else pc + 3


def _jz(self, program, pc):
    return read_data(program[pc + 2]) if read_data(program[pc + 1]) == 0 else pc + 3


def _add(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]) + read_data(program[pc + 3]))
    return pc + 4


def _mult(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]) * read_data(program[pc + 3]))
    return pc + 4


def _mod(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]) % read_data(program[pc + 3]))
    return pc + 4


def _and(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]) & read_data(program[pc + 3]))
    return pc + 4


def _or(self, program, pc):
    write_data(program[pc + 1], read_data(program[pc + 2]) | read_data(program[pc + 3]))
    return pc + 4


def _not(self, program, pc):
    write_data(program[pc + 1], ~read_data(program[pc + 2]))
    return pc + 3


def _rmem(self, program, pc):
    write_data(program[pc + 1], program[read_data(program[pc + 2])])
    return pc + 3


def _wmem(self, program, pc):
    program[read_data(program[pc + 1])] = read_data(program[pc + 2])
    return pc + 3


def _call(self, program, pc):
    stack.append(pc + 2)
    return read_data(program[pc + 1])


def _ret(self, program, pc):
    return stack.pop()


def _out(self, program, pc):
    self.window.addstr(chr(read_data(program[pc + 1])))
    self.window.refresh()
    return pc + 2


def _in(self, program, pc):
    global debug_mode

    show_state(memory, pc)
    self.window.refresh()
    char = self.window.getch()
    if chr(char) == 'Q':
        return -1
    if chr(char) == 'D':
        disassembly(program, 0, len(program))
        return pc
    if chr(char) == 'L':
        return load_state()
    if chr(char) == 'S':
        save_state(program, pc)
        return pc
    if chr(char) == 'R':
        debug_mode = True
        char = 10
    write_data(program[pc + 1], char)
    return pc + 2


def _nop(self, program, pc):
    return pc + 1


def save_state(program, pc):
    global registers, stack
    with open('savestate.pickle', 'wb') as f:
        pickle.dump(registers, f)
        pickle.dump(stack, f)
        pickle.dump(pc, f)
        pickle.dump(program, f)


def load_state():
    global registers, stack, memory
    with open('savestate.pickle', 'rb') as f:
        registers = pickle.load(f)
        stack = pickle.load(f)
        pc = pickle.load(f)
        memory = pickle.load(f)
    return pc


def disassembly(program, pc, length):
    current_length = 0
    with open('dump.txt', 'w') as f:
        while current_length < length:
            opcode = program[pc]
            if opcode in instruction_set:
                f.write('%d:: %s\n' % (pc, instruction_set[opcode].string(program, pc)))
                pc += instruction_set[opcode].length + 1
                current_length += instruction_set[opcode].length + 1
            else:
                f.write('%d:: %d\n' % (pc, program[pc]))
                pc += 1
                current_length += 1


def show_state(program, pc):
    stackwin.clear()
    for i in reversed(range(len(stack))):
        stackwin.addstr(len(stack) - i - 1, 0, 'S%03d:: %05d 0x%05X' % (i, stack[i], stack[i]))
    stackwin.noutrefresh()

    for i in range(len(registers)):
        regwin.addstr(i, 0, 'R%d:: %05d 0x%05X' % (i, registers[i], registers[i]))
    regwin.noutrefresh()

    asmwin.clear()
    current_pc = pc
    pc -= 40
    current_length = 0
    while current_length < 80:
        opcode = program[pc]
        if opcode in instruction_set:
            asmwin.addstr('%d:: %s\n' % (pc, instruction_set[opcode].string(program, pc)), curses.A_BOLD if pc == current_pc else curses.A_NORMAL)
            pc += instruction_set[opcode].length + 1
            current_length += instruction_set[opcode].length + 1
        else:
            asmwin.addstr('%d:: %d\n' % (pc, program[pc]))
            pc += 1
            current_length += 1
        asmwin.noutrefresh()


def main(stdscr):
    global memory, instruction_set, mainwin, regwin, stackwin, asmwin, debug_mode

    if len(sys.argv) != 2:
        logging.error('Incorrect call. Bailing out')
        sys.exit(0)

    curses.curs_set(1)
    curses.echo()

    mainwin = curses.newwin(50, 79, 0, 0)
    mainwin.scrollok(1)
    regwin = curses.newwin(9, 30, 0, 80)
    stackwin = curses.newwin(50, 20, 0, 110)
    asmwin = curses.newwin(40, 30, 9, 80)
    asmwin.scrollok(1)
    logging.basicConfig(filename='interpreter.log', level=logging.WARNING)

    if sys.argv[1] == '-s':
        pc = load_state()
    else:
        with open(sys.argv[1], 'rb') as f:
            memory = [x[0] for x in struct.iter_unpack('<H', f.read())]
        memory.extend([0 for x in range(0x8000 - len(memory))])
        pc = 0

    instruction_set = {
        0: Instruction(0, 0, _halt, mainwin),
        1: Instruction(1, 2, _set, mainwin),
        2: Instruction(2, 1, _push, mainwin),
        3: Instruction(3, 1, _pop, mainwin),
        4: Instruction(4, 3, _eq, mainwin),
        5: Instruction(5, 3, _gt, mainwin),
        6: Instruction(6, 1, _jmp, mainwin),
        7: Instruction(7, 2, _jnz, mainwin),
        8: Instruction(8, 2, _jz, mainwin),
        9: Instruction(9, 3, _add, mainwin),
        10: Instruction(10, 3, _mult, mainwin),
        11: Instruction(11, 3, _mod, mainwin),
        12: Instruction(12, 3, _and, mainwin),
        13: Instruction(13, 3, _or, mainwin),
        14: Instruction(14, 2, _not, mainwin),
        15: Instruction(15, 2, _rmem, mainwin),
        16: Instruction(16, 2, _wmem, mainwin),
        17: Instruction(17, 1, _call, mainwin),
        18: Instruction(18, 0, _ret, mainwin),
        19: Instruction(19, 1, _out, mainwin),
        20: Instruction(20, 1, _in, mainwin),
        21: Instruction(21, 0, _nop, mainwin),
    }

    while pc >= 0:
        opcode = memory[pc]
        try:
            if opcode in instruction_set:
                if debug_mode:
                    show_state(memory, pc)
                    mainwin.refresh()
                    char = mainwin.getch()
                    if chr(char) in ('c', 'C'):
                        debug_mode = False
                pc = instruction_set[opcode].run(memory, pc)
            else:
                logging.error('Unsupported opcode: %d. Exiting' % opcode)
                return
        except IndexError:
            logging.error('Attempted to return or pop with empty stack. Exiting')
            return

if __name__ == '__main__':
    curses.wrapper(main)
