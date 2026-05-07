import sys
import os
import csv
from instructions import REGS, TYPE_R, TYPE_I, TYPE_J

BASE_PC = 0x00400000

def to_bin(val, bits):
    """Retorna val como uma string binária em complemento de dois com largura fixa."""
    return format(val & ((1 << bits) - 1), f'0{bits}b')

def to_hex(val, bits):
    """Retorna val como uma string hexadecimal com largura fixa."""
    return format(val & ((1 << bits) - 1), f'0{bits // 4}x')

def clean(line):
    """Remove comentários inline e normaliza pontuação para espaços."""
    line = line.split('#')[0]
    for char in ",()":
        line = line.replace(char, " ")
    return line.strip()

def main():
    if len(sys.argv) < 3:
        print("Uso: python montador.py entrada.asm -b ou -h")
        return

    input_file = sys.argv[1]
    mode = sys.argv[2]
    
    # Primeira passada: monta a tabela de rótulos
    symbol_table = {}
    valid_instrs = []
    pc = BASE_PC
    
    with open(input_file, 'r') as f:
        for line in f:
            line = clean(line)
            if not line: 
                continue
            if ":" in line:
                label, rest = line.split(":", 1)
                symbol_table[label.strip()] = pc
                line = rest.strip()
            if line:
                valid_instrs.append((pc, line))
                pc += 4

    # Segunda passada: codifica cada instrução
    machine_code = []
    counts = {}
    
    for pc, text in valid_instrs:
        parts = text.split()
        op = parts[0]
        counts[op] = counts.get(op, 0) + 1
        res = ""

        try:
            if op in TYPE_R:
                opcode, funct = TYPE_R[op]
                rs = rt = rd = sa = 0
                if op == "jr": 
                    rs = REGS[parts[1]]
                elif op in ["sll", "srl"]: 
                    rd, rt, sa = REGS[parts[1]], REGS[parts[2]], int(parts[3])
                elif op in ["mfhi", "mflo"]: 
                    rd = REGS[parts[1]]
                elif op in ["mult", "multu", "div", "divu"]: 
                    rs, rt = REGS[parts[1]], REGS[parts[2]]
                else: 
                    rd, rs, rt = REGS[parts[1]], REGS[parts[2]], REGS[parts[3]]
                res = to_bin(opcode, 6) + to_bin(rs, 5) + to_bin(rt, 5) + to_bin(rd, 5) + to_bin(sa, 5) + to_bin(funct, 6)

            elif op in TYPE_I:
                opcode = TYPE_I[op]
                rs = rt = imm = 0
                if op in ["beq", "bne"]:
                    rs, rt = REGS[parts[1]], REGS[parts[2]]
                    imm = (symbol_table[parts[3]] - (pc + 4)) // 4
                elif op in ["lw", "sw"]:
                    rt, imm, rs = REGS[parts[1]], int(parts[2]), REGS[parts[3]]
                elif op == "lui": 
                    rt, imm = REGS[parts[1]], int(parts[2])
                else: 
                    rt, rs, imm = REGS[parts[1]], REGS[parts[2]], int(parts[3])
                res = to_bin(opcode, 6) + to_bin(rs, 5) + to_bin(rt, 5) + to_bin(imm, 16)

            elif op in TYPE_J:
                opcode = TYPE_J[op]
                addr = symbol_table[parts[1]] // 4
                res = to_bin(opcode, 6) + to_bin(addr, 26)
            else:
                raise ValueError(f"Instrução desconhecida: {op}")

            machine_code.append(res)
        except (KeyError, IndexError, ValueError) as e:
            print(f"Erro na instrução no PC {hex(pc)}: {text} ({e})")
            return

    # Geração da saída
    out_ext = ".bin" if mode == "-b" else ".hex"
    out_file = os.path.splitext(input_file)[0] + out_ext
    with open(out_file, 'w') as f:
        if mode == '-h':
            f.write("v2.0 raw\n")
            for b in machine_code: f.write(f"{to_hex(int(b, 2), 32)}\n")
        else:
            f.write("\n".join(machine_code) + "\n")

    # Estatísticas de CPI
    total_inst = len(machine_code)
    total_cycles = 0
    cycle_map = {}
    if os.path.exists("cycles.csv"):
        with open("cycles.csv", 'r') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2: cycle_map[row[0].strip()] = int(row[1].strip())
    
    print("\nRelatório de Execução:")
    for inst, q in counts.items():
        print(f"{inst}: {q}")
        total_cycles += q * cycle_map.get(inst, 1)

    print(f"\nCPI médio: {total_cycles / total_inst if total_inst > 0 else 0:.2f}")
    print(f"Arquivo gerado com sucesso: {out_file}")

if __name__ == "__main__":
    main()