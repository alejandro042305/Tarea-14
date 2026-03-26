import tkinter as tk
from tkinter import filedialog
from computer import Computer


class NB64GUI:

    def __init__(self):

        self.comp = Computer()

        self.root = tk.Tk()
        self.root.title("NB-64 Computer — Arquitectura Von Neumann")
        self.root.geometry("1200x700")

        self.create_widgets()
        self.update_view()


    def create_widgets(self):

        top = tk.Frame(self.root)
        top.pack(fill="x")

        tk.Button(top,text="Cargar Programa",command=self.load).pack(side="left")
        tk.Button(top,text="Step",command=self.step).pack(side="left")
        tk.Button(top,text="Run",command=self.run).pack(side="left")
        tk.Button(top,text="Reset",command=self.reset).pack(side="left")

        main = tk.Frame(self.root)
        main.pack(fill="both",expand=True)

        self.mem = tk.Text(main,width=60)
        self.mem.pack(side="left",fill="both",expand=True)

        right = tk.Frame(main)
        right.pack(side="right",fill="y")

        self.reg = tk.Text(right,width=40)
        self.reg.pack()

        self.flags = tk.Label(right,text="Flags")
        self.flags.pack()


    def load(self):

        file = filedialog.askopenfilename()

        if file:
            self.comp.loader.load_program(file)
            self.update_view()


    def step(self):

        if not self.comp.cpu.halted:
            self.comp.cpu.step()
            self.update_view()


    def run(self):

        self.comp.cpu.run()
        self.update_view()


    def reset(self):

        self.comp.reset()
        self.update_view()


    def update_view(self):

        self.mem.delete("1.0",tk.END)

        for i in range(256):
            self.mem.insert(tk.END,f"{i:03}: {self.comp.ram.read(i)}\n")

        r = self.comp.regs

        self.reg.delete("1.0",tk.END)

        self.reg.insert(tk.END,f"PC: {r.PC}\n")
        self.reg.insert(tk.END,f"SP: {r.SP}\n")
        self.reg.insert(tk.END,f"IR: {r.IR}\n\n")

        for i in range(8):
            self.reg.insert(tk.END,f"R{i}: {r.get_reg(i)}\n")

        self.flags.config(
            text=f"Z:{r.flag_Z}  C:{r.flag_C}  N:{r.flag_N}  V:{r.flag_V}"
        )


    def start(self):
        self.root.mainloop()