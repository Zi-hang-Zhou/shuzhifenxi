import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
from interpolation import ManualInterpolationEngine

class ResizableImageAppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Python大作业 - 拖拽/窗口输入双模式")
        self.root.geometry("1100x850")

        self.engine = ManualInterpolationEngine()
        self.original_array = None
        self.current_image = None
        self.tk_image = None

        # 状态变量
        self.img_x, self.img_y = 50, 50
        self.img_w, self.img_h = 0, 0
        self.drag_data = {"item": None, "x": 0, "y": 0, "type": None}
        self.mode = tk.StringVar(value="drag")  # "drag" or "window"
        self.lock_ratio = tk.BooleanVar(value=False)
        self.scale_var = tk.DoubleVar(value=1.0)
        self.input_w = tk.IntVar(value=0)
        self.input_h = tk.IntVar(value=0)

        # 顶部按钮区
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="打开图片", command=self.load_image).pack(side=tk.LEFT, padx=10)
        tk.Label(btn_frame, text="操作提示：拖拽红框或窗口输入目标尺寸").pack(side=tk.LEFT, padx=10)

        # 模式切换按钮
        self.mode_btn = tk.Button(btn_frame, text="切换为窗口输入模式", command=self.toggle_mode)
        self.mode_btn.pack(side=tk.RIGHT, padx=10)

        # 插值算法选择
        self.method_var = tk.StringVar(value="bilinear")
        method_menu = tk.OptionMenu(btn_frame, self.method_var, "nearest", "bilinear", "biquadratic", "bicubic")
        method_menu.pack(side=tk.RIGHT, padx=10)
        tk.Label(btn_frame, text="插值算法:").pack(side=tk.RIGHT)

        # 画布
        self.canvas = tk.Canvas(root, bg="gray", width=900, height=700)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 窗口输入区
        self.input_frame = tk.Frame(root)
        self.input_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.input_frame, text="宽:").pack(side=tk.LEFT)
        self.entry_w = tk.Entry(self.input_frame, textvariable=self.input_w, width=6)
        self.entry_w.pack(side=tk.LEFT)
        tk.Label(self.input_frame, text="高:").pack(side=tk.LEFT)
        self.entry_h = tk.Entry(self.input_frame, textvariable=self.input_h, width=6)
        self.entry_h.pack(side=tk.LEFT)
        tk.Label(self.input_frame, text="缩放倍数:").pack(side=tk.LEFT)
        self.entry_scale = tk.Entry(self.input_frame, textvariable=self.scale_var, width=6)
        self.entry_scale.pack(side=tk.LEFT)
        self.lock_cb = tk.Checkbutton(self.input_frame, text="锁定比例", variable=self.lock_ratio, command=self.on_lock_ratio)
        self.lock_cb.pack(side=tk.LEFT, padx=10)
        self.apply_btn = tk.Button(self.input_frame, text="应用缩放", command=self.apply_window_resize)
        self.apply_btn.pack(side=tk.LEFT, padx=10)

        # 绑定输入事件
        self.entry_w.bind("<KeyRelease>", self.on_input_w)
        self.entry_h.bind("<KeyRelease>", self.on_input_h)
        self.entry_scale.bind("<KeyRelease>", self.on_input_scale)

        # 默认隐藏窗口输入区
        self.input_frame.pack_forget()

        # 绑定画布事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def toggle_mode(self):
        if self.mode.get() == "drag":
            self.mode.set("window")
            self.mode_btn.config(text="切换为拖拽模式")
            self.input_frame.pack(fill=tk.X, pady=5)
        else:
            self.mode.set("drag")
            self.mode_btn.config(text="切换为窗口输入模式")
            self.input_frame.pack_forget()

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not file_path: return
        pil_img = Image.open(file_path).convert("RGB")
        self.original_array = np.array(pil_img)
        self.current_image = pil_img
        self.img_w, self.img_h = pil_img.size
        self.input_w.set(self.img_w)
        self.input_h.set(self.img_h)
        self.scale_var.set(1.0)
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        if self.current_image is None: return
        self.tk_image = ImageTk.PhotoImage(self.current_image)
        self.canvas.create_image(self.img_x, self.img_y, image=self.tk_image, anchor="nw", tags="image")
        x1, y1 = self.img_x, self.img_y
        x2, y2 = x1 + self.img_w, y1 + self.img_h
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", dash=(4, 4), tags="frame")
        mid_x, mid_y = x1 + self.img_w/2, y1 + self.img_h/2
        handles = [
            (x1, y1, "nw"), (mid_x, y1, "n"), (x2, y1, "ne"),
            (x2, mid_y, "e"), (x2, y2, "se"), (mid_x, y2, "s"),
            (x1, y2, "sw"), (x1, mid_y, "w")
        ]
        r = 5
        for hx, hy, tag in handles:
            self.canvas.create_rectangle(hx-r, hy-r, hx+r, hy+r, fill="white", outline="black", tags=("handle", tag))

    def on_press(self, event):
        if self.mode.get() != "drag": return
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)
        if "handle" in tags:
            handle_type = [t for t in tags if t in ["nw","n","ne","e","se","s","sw","w"]][0]
            self.drag_data = {"item": item, "x": event.x, "y": event.y, "type": handle_type}
        elif "image" in tags:
            self.drag_data = {"item": item, "x": event.x, "y": event.y, "type": "move"}
        else:
            self.drag_data = {"type": None}

    def on_drag(self, event):
        if self.mode.get() != "drag": return
        if self.drag_data["type"] is None: return
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        handle = self.drag_data["type"]
        if handle == "move":
            self.img_x += dx
            self.img_y += dy
        else:
            if "e" in handle: self.img_w += dx
            if "w" in handle: self.img_x += dx; self.img_w -= dx
            if "s" in handle: self.img_h += dy
            if "n" in handle: self.img_y += dy; self.img_h -= dy
            if self.img_w < 10: self.img_w = 10
            if self.img_h < 10: self.img_h = 10
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.redraw_canvas()

    def on_release(self, event):
        if self.mode.get() != "drag": return
        if self.drag_data["type"] is None: return
        if self.drag_data["type"] == "move": return
        method = self.method_var.get()
        self.engine.set_method(method)
        print(f"拖拽重采样: {int(self.img_w)} x {int(self.img_h)}，算法: {method}")
        new_arr = self.engine.process_image(self.original_array, self.img_w, self.img_h)
        self.current_image = Image.fromarray(new_arr)
        self.input_w.set(self.img_w)
        self.input_h.set(self.img_h)
        self.scale_var.set(self.img_w / self.original_array.shape[1])
        self.redraw_canvas()
        self.drag_data["type"] = None

    def on_input_w(self, event=None):
        if not self.lock_ratio.get(): return
        try:
            w = int(self.entry_w.get())
            orig_w, orig_h = self.original_array.shape[1], self.original_array.shape[0]
            h = int(round(w * orig_h / orig_w))
            self.input_h.set(h)
            self.scale_var.set(w / orig_w)
        except Exception:
            pass

    def on_input_h(self, event=None):
        if not self.lock_ratio.get(): return
        try:
            h = int(self.entry_h.get())
            orig_w, orig_h = self.original_array.shape[1], self.original_array.shape[0]
            w = int(round(h * orig_w / orig_h))
            self.input_w.set(w)
            self.scale_var.set(w / orig_w)
        except Exception:
            pass

    def on_input_scale(self, event=None):
        try:
            scale = float(self.entry_scale.get())
            orig_w, orig_h = self.original_array.shape[1], self.original_array.shape[0]
            w = int(round(orig_w * scale))
            h = int(round(orig_h * scale))
            if self.lock_ratio.get():
                self.input_w.set(w)
                self.input_h.set(h)
        except Exception:
            pass

    def on_lock_ratio(self):
        if not self.original_array is None:
            orig_w, orig_h = self.original_array.shape[1], self.original_array.shape[0]
            w = self.input_w.get()
            h = self.input_h.get()
            if self.lock_ratio.get():
                # 以宽为主自动调整高
                h = int(round(w * orig_h / orig_w))
                self.input_h.set(h)
                self.scale_var.set(w / orig_w)

    def apply_window_resize(self):
        if self.original_array is None: return
        try:
            w = int(self.entry_w.get())
            h = int(self.entry_h.get())
            if w < 5 or h < 5:
                messagebox.showerror("错误", "宽高太小")
                return
            method = self.method_var.get()
            self.engine.set_method(method)
            print(f"窗口输入重采样: {w} x {h}，算法: {method}")
            new_arr = self.engine.process_image(self.original_array, w, h)
            self.current_image = Image.fromarray(new_arr)
            self.img_w, self.img_h = w, h
            self.redraw_canvas()
        except Exception as e:
            messagebox.showerror("错误", f"输入有误: {e}")