# NB-64 Computer Simulator

<div align="center">

**Simulador de Computadora de 8 bits con Arquitectura Von Neumann**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

## 📋 Descripción

**NB-64** es un simulador educativo completo de una arquitectura computacional de 8 bits que implementa:

- **Memoria RAM**: 256 bytes direccionables
- **CPU de 8 bits**: con ciclo FETCH-DECODE-EXECUTE
- **8 Registros**: R0-R7 para datos generales
- **Registros especiales**: PC (Program Counter), SP (Stack Pointer), IR (Instruction Register)
- **Banderas de condición**: Z (Zero), C (Carry), N (Negative), V (Overflow)
- **Coprocesador FPU**: IEEE 754 de doble precisión con operaciones extendidas
- **40+ instrucciones**: organizadas en 4 tamaños diferentes

## 🏗️ Arquitectura

### Von Neumann
El simulador implementa la arquitectura Von Neumann donde código y datos comparten el mismo espacio de memoria (256 bytes).

```
┌─────────────────────────────────────┐
│         MEMORIA RAM (256 bytes)     │
│  Contiene código + datos            │
│  Direccionable por byte             │
└─────────────────────────────────────┘
           ↕
┌─────────────────────────────────────┐
│       CPU CORE (FETCH-DECODE)      │
│  • 8 registros generales (R0-R7)   │
│  • Program Counter (48 bits)        │
│  • Stack Pointer (48 bits)          │
│  • Instruction Register             │
└─────────────────────────────────────┘
           ↕
┌─────────────────────────────────────┐
│   FPU COPROCESSOR (IEEE 754)       │
│  • Operaciones en punto flotante    │
│  • Método de Heron (√)              │
│  • Constante de Brun                │
└─────────────────────────────────────┘
```

## 📦 Estructura del Proyecto

```
NB64 COMPU/
├── README.md                          # Este archivo
├── NB64_COMPU_COMPLETO.py            # Simulador completo integrado
├── docs/
│   └── INSTRUCCIONES.txt             # Guía de instrucciones
├── src/
│   ├── computer.py                   # Orquestador principal
│   ├── cpu_core.py                   # Núcleo del CPU
│   ├── instructions.py               # Set de instrucciones
│   ├── ram.py                        # Memoria RAM
│   ├── registers.py                  # Registros
│   ├── fpu.py                        # Coprocesador FPU
│   ├── loader.py                     # Cargador de programas
│   ├── gui.py                        # GUI (interfaz gráfica)
│   └── main_gui.py                   # Punto de entrada GUI
└── programs/
    └── examples/
        ├── suma.txt                  # Ejemplo: suma (5 + 3 = 8)
        ├── multiplicacion.txt        # Ejemplo: 4 × 6 = 24
        ├── division.txt              # Ejemplo: 16 ÷ 4 = 4
        ├── operaciones_logicas.txt   # Ejemplo: AND, XOR
        ├── halt.txt                  # Ejemplo: detener CPU
        ├── heron.txt                 # Ejemplo: √125 (método Heron)
        ├── brun.txt                  # Ejemplo: Constante de Brun
        └── fpu_lib.txt               # Ejemplo: operaciones FPU
```

## 🔧 Componentes Principales

### 1. RAM (Memoria)
- 256 bytes direccionables por byte
- Cada byte es almacenado como string binario de 8 bits
- Direcciones especiales para FPU (0xE0-0xF9)

### 2. Registros
- **R0-R7**: Registros de 8 bits para propósito general
- **PC**: Program Counter de 48 bits
- **SP**: Stack Pointer de 48 bits (crece hacia abajo)
- **Banderas**: Z, C, N, V

### 3. CPU Core
Implementa el ciclo de instrucción:
1. **FETCH**: Obtiene la instrucción de memoria
2. **DECODE**: Identifica el opcode y parámetros
3. **EXECUTE**: Ejecuta la instrucción

### 4. FPU (Coprocesador)
Operaciones en punto flotante IEEE 754:
- Aritmética básica: ADD, SUB, MUL, DIV, SQRT
- Método de Heron para raíz cuadrada
- Constante de Brun (suma de inversos de primos gemelos)

## 📚 Conjunto de Instrucciones

### Tamaños de Instrucción

| Tamaño | Prefijo | Ejemplos |
|--------|---------|----------|
| 1 byte | `00` | NOP, HALT, RET, FPU_OP |
| 2 bytes | `01` | MOV, ADD, SUB, MUL, DIV, AND, XOR |
| 4 bytes | `10` | MOVI (cargar inmediato) |
| 8 bytes | `11` | LOAD, STORE, JMP, JZ, JNZ, CALL |

### Categorías de Instrucciones

#### Movimiento de Datos
```
MOV Ra, Rb       # Copia Rb a Ra
PUSH Ra          # Guarda Ra en stack
POP Ra           # Recupera valor del stack en Ra
LOAD Ra, [Addr]  # Carga desde memoria
STORE [Addr], Ra # Guarda en memoria
XCHG Ra, Rb      # Intercambia valores
LEA Ra, Addr     # Load Effective Address
```

#### Aritmética
```
ADD Ra, Rb       # Ra = Ra + Rb
SUB Ra, Rb       # Ra = Ra - Rb
MUL Ra, Rb       # Ra = Ra * Rb
DIV Ra, Rb       # Ra = Ra / Rb
ADC Ra, Rb       # Ra = Ra + Rb + Carry
SBB Ra, Rb       # Ra = Ra - Rb - Carry
INC Ra           # Ra = Ra + 1
DEC Ra           # Ra = Ra - 1
NEG Ra           # Ra = -Ra
```

#### Lógica y Desplazamiento
```
AND Ra, Rb       # Ra = Ra & Rb
XOR Ra, Rb       # Ra = Ra ^ Rb
XORA Ra, Rb      # Ra = ~(Ra ^ Rb)
NOT Ra           # Ra = ~Ra
SHL Ra           # Ra = Ra << 1
SHR Ra           # Ra = Ra >> 1
ROL Ra           # Ra = (Ra << 1) | (Ra >> 7)
ROR Ra           # Ra = (Ra >> 1) | ((Ra & 1) << 7)
CMP Ra, Rb       # Compara Ra vs Rb
TEST Ra, Rb      # Test Ra & Rb
```

#### Control de Flujo
```
JMP Addr         # Salto incondicional
JZ Addr          # Salto si zero flag = 1
JNZ Addr         # Salto si zero flag = 0
JC Addr          # Salto si carry flag = 1
JNC Addr         # Salto si carry flag = 0
CALL Addr        # Llamada a subrutina
RET              # Retorno de subrutina
IRET             # Retorno de interrupción
```

#### Sistema
```
NOP              # No-operation
HALT             # Detiene el CPU
FPU_OP           # Ejecuta operación del FPU
INT              # Interrupción
```

## 🚀 Uso

### Instalación

```bash
git clone https://github.com/alejandro042305/Tarea-14.git
cd "NB64 COMPU"
```

### Uso Básico (Python)

```python
from src.computer import Computer

# Crear instancia de la computadora
computadora = Computer()

# Cargar un programa
computadora.load_program('programs/examples/suma.txt')

# Ejecutar
computadora.cpu.run(max_cycles=10000)

# Ver estado
computadora.show_state()
```

### Ejemplo: Suma (5 + 3 = 8)

**Programa en binario**:
```
10000000 00000101 00000000 00000000    # MOVI R0, 5
10000000 00010011 00000000 00000000    # MOVI R1, 3
01001000 00000010                      # ADD R0, R1
00000001                               # HALT
```

**Resultado**:
- R0 = 8 (resultado de 5 + 3)
- Flag Z = 0 (no es cero)
- Flag C = 0 (sin carry)

## 🔬 Algoritmos Implementados

### Método de Heron (Raíz Cuadrada)

Iteración: `y_{i+1} = (1/2) × (y_i + x/y_i)`

**Convergencia para √125**:
- Iteración 0: y = 10.0 (inicial)
- Iteración 1: y ≈ 11.25
- Iteración 2: y ≈ 11.18056
- Iteración 3: y ≈ 11.18034 (converge)

### Constante de Brun

`B₂ = Σ(1/p + 1/q)` para pares de primos gemelos

**Pares (p, q=p+2)**:
- (3,5), (5,7), (11,13), (17,19), (29,31)
- (41,43), (59,61), (71,73), (101,103), (107,109)

**Valor**: B₂ ≈ 1.902160583104...

## 📝 Ejemplos Incluidos

### 1. suma.txt
Suma 5 + 3 = 8

### 2. multiplicacion.txt
Multiplica 4 × 6 = 24

### 3. division.txt
Divide 16 ÷ 4 = 4

### 4. operaciones_logicas.txt
Operaciones AND y XOR entre números

### 5. halt.txt
Instrucción simple HALT

### 6. heron.txt
Calcula √125 usando método de Heron (5 iteraciones)

### 7. brun.txt
Calcula la Constante de Brun (suma de 10 pares de primos gemelos)

### 8. fpu_lib.txt
Demuestra operaciones FPU: ADD, SUB, MUL, DIV

## 🎯 Protocolo FPU

### Direcciones en RAM

| Dirección | Descripción |
|-----------|-------------|
| 0xE0-0xE7 | Operando A (float64, big-endian) |
| 0xE8-0xEF | Operando B (float64, big-endian) |
| 0xF0 | Código de operación |
| 0xF1-0xF8 | Resultado (escrito por FPU) |
| 0xF9 | Flags FPU |
| 0xFA-0xFC | Parámetros para operaciones extendidas |

### Códigos de Operación

```
0x01 = ADD       (A + B)
0x02 = SUB       (A - B)
0x03 = MUL       (A × B)
0x04 = DIV       (A ÷ B)
0x05 = SQRT      (√A)
0x06 = CMP       (Comparación)
0x10 = HERON_STEP (Iteración de Heron)
0x20 = BRUN_ACCUMULATE (Constante de Brun)
```

## 📖 Documentación Adicional

Ver [docs/INSTRUCCIONES.txt](docs/INSTRUCCIONES.txt) para guía completa de instrucciones.

## 🏆 Características

✅ Arquitectura Von Neumann completa  
✅ CPU de 8 bits con 40+ instrucciones  
✅ Coprocesador FPU IEEE 754  
✅ Sistema de banderas de condición  
✅ Stack pointer para subrutinas  
✅ Métodos numéricos (Heron, Brun)  
✅ Cargador de programas binarios  
✅ Interfaz gráfica (GUI)  
✅ Ejemplos educativos completos  

## 👤 Autor

Alejandro

## 📄 Licencia

MIT License - Ver LICENSE para detalles

## 🔗 Enlaces

- **GitHub**: https://github.com/alejandro042305/Tarea-14
- **Instrucciones detalladas**: [docs/INSTRUCCIONES.txt](docs/INSTRUCCIONES.txt)

## 📞 Contacto

Para preguntas o sugerencias, abre un issue en GitHub.

---

**Última actualización**: 2026-03-28  
**Versión**: 1.0
