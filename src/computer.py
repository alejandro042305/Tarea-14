from ram import RAM
from registers import Registers
from loader import Loader
from cpu_core import CPUCore
from fpu import FPU


class Computer:

    def __init__(self):
        self.ram    = RAM(256)
        self.regs   = Registers()
        self.loader = Loader(self.ram._memory)
        self.fpu    = FPU(self.ram)
        self.cpu    = CPUCore(self.ram, self.regs, fpu=self.fpu)

    def reset(self):
        self.ram    = RAM(256)
        self.regs   = Registers()
        self.loader = Loader(self.ram._memory)
        self.fpu    = FPU(self.ram)
        self.cpu    = CPUCore(self.ram, self.regs, fpu=self.fpu)
