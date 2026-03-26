# 📁 Carpeta: src

Esta carpeta contiene todo el código fuente Python del simulador NB-64.

## Archivos

- **main_gui.py** - Punto de entrada del programa. Ejecuta esto primero:
  ```bash
  python main_gui.py
  ```

- **gui.py** - Interfaz gráfica con Tkinter (botones, display RAM, registros)

- **computer.py** - Integración: conecta CPU, RAM, registros y loader

- **cpu_core.py** - Núcleo del CPU:
  - Fetch: lee instrucciones de memoria
  - Decode: decodifica instrucciones
  - Execute: ejecuta operaciones

- **ram.py** - Memoria RAM (256 bytes)
  - read(addr) - leer byte
  - write(addr, data) - escribir byte

- **registers.py** - Registros de la CPU:
  - R0-R7 (8 registros de 8 bits)
  - PC (Program Counter)
  - SP (Stack Pointer)
  - IR (Instruction Register)
  - Flags: Z, C, N, V

- **instructions.py** - Conjunto de instrucciones (30+):
  - Tipo A: Movimiento y transferencia
  - Tipo B: Operaciones aritméticas
  - Tipo C: Operaciones lógicas
  - Tipo D: Saltos (jumps)
  - Tipo E: Control

- **loader.py** - Cargador de programas:
  - Carga archivos .txt con instrucciones binarias
  - Valida formato (8 bits por línea)

## Bugs Corregidos (v2.0)

✅ cpu_core.py - Ciclo duplicado en run()
✅ instructions.py - JNZ, JC, JNC sin validar rango de memoria
