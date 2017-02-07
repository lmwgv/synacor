import sys
import struct
import logging

registers = [0 for x in range(8)]
stack = []


def read_data(value):
    if value <= 0x7FFF:
        return value
    return registers[value - 0x8000]


def write_data(destination, value):
    if destination <= 0x7FFF:
        logging.error('Invalid register number')
        sys.exit(0)
    registers[destination - 0x8000] = value % 0x8000
    logging.info('Set register %d to %d' % (destination - 0x8000, value % 0x8000))


def interpret(program, pc):
    opcode = program[pc]
    logging.info('Processing opcode %d at %d' % (opcode, pc))
    pc += 1

    # halt
    if opcode == 0:
        logging.info('Received opcode 0. Exiting')
        sys.exit(1)
    # set
    elif opcode == 1:
        logging.info('Received set with operands %d %d' % (program[pc], read_data(program[pc + 1])))
        write_data(program[pc], read_data(program[pc + 1]))
        pc += 2
    # push
    elif opcode == 2:
        logging.info('Received push with operand %d' % read_data(program[pc]))
        stack.append(read_data(program[pc]))
        pc += 1
    # pop
    elif opcode == 3:
        logging.info('Received pop with operand %d' % program[pc])
        if not len(stack):
            logging.error('Attempted to pop from empty stack. Exiting')
            sys.exit(0)
        write_data(program[pc], stack.pop())
        pc += 1
    # eq
    elif opcode == 4:
        logging.info('Received eq with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], 1 if read_data(program[pc + 1]) == read_data(program[pc + 2]) else 0)
        pc += 3
    # gt
    elif opcode == 5:
        logging.info('Received gt with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], 1 if read_data(program[pc + 1]) > read_data(program[pc + 2]) else 0)
        pc += 3
    # jmp
    elif opcode == 6:
        pc = read_data(program[pc])
        logging.info('Jumping to %d' % pc)
    # jt
    elif opcode == 7:
        logging.info('Received jump if not zero with operands %d %d' % (read_data(program[pc]), read_data(program[pc + 1])))
        if read_data(program[pc]) != 0:
            pc = read_data(program[pc + 1])
            logging.info('Jumping to %d' % pc)
        else:
            pc += 2
    # jz
    elif opcode == 8:
        logging.info('Received jump if zero with operands %d %d' % (read_data(program[pc]), read_data(program[pc + 1])))
        if read_data(program[pc]) == 0:
            pc = read_data(program[pc + 1])
            logging.info('Jumping to %d' % pc)
        else:
            pc += 2
    # add
    elif opcode == 9:
        logging.info('Received add with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], read_data(program[pc + 1]) + read_data(program[pc + 2]))
        pc += 3
    # mult
    elif opcode == 10:
        logging.info('Received mult with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], read_data(program[pc + 1]) * read_data(program[pc + 2]))
        pc += 3
    # mod
    elif opcode == 11:
        logging.info('Received mod with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], read_data(program[pc + 1]) % read_data(program[pc + 2]))
        pc += 3
    # and
    elif opcode == 12:
        logging.info('Received and with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], read_data(program[pc + 1]) & read_data(program[pc + 2]))
        pc += 3
    # or
    elif opcode == 13:
        logging.info('Received or with operands %d %d %d' % (program[pc], read_data(program[pc + 1]), read_data(program[pc + 2])))
        write_data(program[pc], read_data(program[pc + 1]) | read_data(program[pc + 2]))
        pc += 3
    # not
    elif opcode == 14:
        logging.info('Received not with operands %d %d' % (program[pc], read_data(program[pc + 1])))
        write_data(program[pc], ~read_data(program[pc + 1]))
        pc += 2
    # rmem
    elif opcode == 15:
        logging.info('Received rmem with operands %d %d' % (program[pc], read_data(program[pc + 1])))
        write_data(program[pc], program[read_data(program[pc + 1])])
        pc += 2
    # wmem
    elif opcode == 16:
        logging.info('Received wmem with operands %d %d' % (read_data(program[pc]), read_data(program[pc + 1])))
        program[read_data(program[pc])] = read_data(program[pc + 1])
        pc += 2
    # call
    elif opcode == 17:
        logging.info('Received call with operand %d' % read_data(program[pc]))
        stack.append(pc + 1)
        pc = read_data(program[pc])
        logging.info('Jumping to %d' % pc)
    # ret
    elif opcode == 18:
        logging.info('Received return')
        if len(stack) == 0:
            logging.error('Attempted to return with empty stack. Exiting')
            sys.exit(0)
        pc = stack.pop()
        logging.info('Jumping to %d' % pc)
    # out
    elif opcode == 19:
        logging.info('Printing %d' % read_data(program[pc]))
        sys.stdout.write(chr(read_data(program[pc])))
        pc += 1
    # in
    elif opcode == 20:
        logging.info('Received in with operand %d' % program[pc])
        write_data(program[pc], ord(sys.stdin.read(1)))
        pc += 1
    # nop
    elif opcode == 21:
        logging.info('Nop received. Passing')
        pass
    else:
        logging.error('Unsupported opcode: %d. Exiting' % opcode)
        sys.exit(0)

    return pc


def run(program):
    pc = 0
    exit = False

    while not exit:
        pc = interpret(program, pc)

if __name__ == '__main__':
    logging.basicConfig(filename='interpreter.log', level=logging.WARNING)

    if len(sys.argv) != 2:
        logging.error('Incorrect call. Bailing out')
        sys.exit(0)

    with open(sys.argv[1], 'rb') as f:
        memory = [x[0] for x in struct.iter_unpack('<H', f.read())]
    memory.extend([0 for x in range(0x8000 - len(memory))])

    run(memory)
