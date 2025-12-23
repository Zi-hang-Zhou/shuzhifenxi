import tkinter as tk
from gui import ResizableImageAppWindow as ResizableImageApp

if __name__ == "__main__":
    root = tk.Tk()
    app = ResizableImageApp(root)
    root.mainloop()