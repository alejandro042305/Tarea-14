
class Loader:
    def __init__(self, memory: list):
        self.memory = memory

    def load_program(self, source, base_address: int = 0, manual: bool = False) -> None:
        """Carga un programa en la memoria desde archivo o entrada manual."""
        if manual and isinstance(source, tuple):
            addr, instr = source
            self._write_instruction(addr, instr)
        else:
            with open(source, 'r') as f:
                # CORRECCIÓN: contador separado, solo sube en líneas de datos válidos
                byte_index = 0
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    # Saltar líneas vacías y comentarios SIN avanzar byte_index
                    if not line or line.startswith('#'):
                        continue
                    if len(line) != 8 or not all(c in '01' for c in line):
                        raise ValueError(
                            f"Línea {line_num}: formato inválido '{line}' "
                            f"(debe ser exactamente 8 bits binarios)"
                        )
                    target = base_address + byte_index
                    if target >= len(self.memory):
                        raise IndexError(
                            f"Línea {line_num}: dirección {target} fuera de rango "
                            f"[0, {len(self.memory)-1}]"
                        )
                    self.memory[target] = line
                    byte_index += 1

    def _write_instruction(self, addr: int, bits: str) -> None:
        """Escribe una instrucción multi-byte en direcciones consecutivas."""
        if len(bits) % 8 != 0:
            raise ValueError(
                f"Instrucción debe tener longitud múltiplo de 8 bits, "
                f"tiene {len(bits)} bits"
            )
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            target = addr + i // 8
            if target >= len(self.memory):
                raise IndexError(f"Dirección {target} fuera de rango")
            self.memory[target] = byte