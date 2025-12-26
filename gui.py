import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
from interpolation import InterpolationEngine

class ResizableImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("2D图像缩放 - 拖拽/窗口输入双模式")
        self.root.geometry("1000x750")

        # 基本功能
        # 插值引擎
        self.engine = InterpolationEngine()
        self.original_array = None  # 原始图片数据
        self.current_image = None   # 当前显示的PIL图片
        self.tk_image = None        # Tkinter显示图片

        # 状态变量
        self.img_x, self.img_y = 50, 50
        self.img_w, self.img_h = 0, 0
        self.drag_data = {"item": None, "x": 0, "y": 0, "type": None}
        self.mode = tk.StringVar(value="drag")  # 拖拽/窗口输入模式
        self.lock_ratio = tk.BooleanVar(value=False)  # 是否锁定长宽比
        self.scale_var = tk.DoubleVar(value=1.0)      # 缩放倍数
        self.input_w = tk.IntVar(value=0)             # 输入宽
        self.input_h = tk.IntVar(value=0)             # 输入高

        # GUI界面
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="打开图片", command=self.load_image).pack(side=tk.LEFT, padx=20)
        tk.Label(
            btn_frame,
            text="两种模式：\n 1. 拖拽红框手动缩放\n 2. 窗口输入目标尺寸或锁定比例后输入缩放倍数\n可切换插值算法",
            justify="left",
            font=("微软雅黑", 11)
        ).pack(side=tk.LEFT, padx=20)

        # 模式切换
        self.mode_btn = tk.Button(btn_frame, text="切换为窗口输入模式", command=self.toggle_mode)
        self.mode_btn.pack(side=tk.RIGHT, padx=10)

        # 插值算法选择
        self.method_var = tk.StringVar(value="bilinear")
        method_menu = tk.OptionMenu(btn_frame, self.method_var, "nearest", "bilinear", "biquadratic", "bicubic")
        method_menu.pack(side=tk.RIGHT, padx=10)
        tk.Label(btn_frame, text="插值算法:").pack(side=tk.RIGHT)

        # 撤销、回到原图、保存
        self.undo_stack = []  # 撤销历史栈
        tk.Button(btn_frame, text="保存图片", command=self.save_image).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="回到原图", command=self.reset_image).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="撤销", command=self.undo).pack(side=tk.RIGHT, padx=10)

        # 画布显示
        self.canvas = tk.Canvas(root, bg="gray", width=600, height=400)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 窗口输入区 
        self.input_frame = tk.Frame(root)
        self.input_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.input_frame, text="高:", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT, padx=(5,0))
        self.entry_h = tk.Entry(self.input_frame, textvariable=self.input_h, width=30)
        self.entry_h.pack(side=tk.LEFT, padx=(0,5))
        tk.Label(self.input_frame, text="宽:", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.entry_w = tk.Entry(self.input_frame, textvariable=self.input_w, width=30)
        self.entry_w.pack(side=tk.LEFT, padx=(0,5))
        tk.Label(self.input_frame, text="缩放倍数:", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.entry_scale = tk.Entry(self.input_frame, textvariable=self.scale_var, width=36)
        self.entry_scale.pack(side=tk.LEFT, padx=(0,5))
        self.lock_cb = tk.Checkbutton(self.input_frame, text="锁定比例", variable=self.lock_ratio, command=self.on_lock_ratio, font=("微软雅黑", 12, "bold"))
        self.lock_cb.pack(side=tk.LEFT, padx=(0,5))
        self.apply_btn = tk.Button(self.input_frame, text="应用缩放", command=self.apply_window_resize)
        self.apply_btn.pack(side=tk.LEFT, padx=(0,5))

        # 绑定输入事件
        self.entry_w.bind("<KeyRelease>", self.on_input_w)
        self.entry_h.bind("<KeyRelease>", self.on_input_h)
        self.entry_scale.bind("<KeyRelease>", self.on_input_scale)

        # 默认隐藏窗口输入区（附加功能）
        self.input_frame.pack_forget()

        # 绑定画布事件（拖拽缩放，附加功能）
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    # 模式切换
    def toggle_mode(self):
        if self.mode.get() == "drag":
            self.mode.set("window")
            self.mode_btn.config(text="切换为拖拽模式")
            self.input_frame.pack(fill=tk.X, pady=5)
        else:
            self.mode.set("drag")
            self.mode_btn.config(text="切换为窗口输入模式")
            self.input_frame.pack_forget()

    # 加载图片并适配显示
    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not file_path: return
        pil_img = Image.open(file_path).convert("RGB")
        self.original_array = np.array(pil_img)

        # 获取画布大小，并预留边距
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        margin = 20  # 上下左右各留20像素
        if canvas_w < 10 or canvas_h < 10:
            canvas_w = int(self.canvas['width'])
            canvas_h = int(self.canvas['height'])
        avail_w = canvas_w - 2 * margin
        avail_h = canvas_h - 2 * margin

        img_w, img_h = pil_img.size
        scale = min(avail_w / img_w, avail_h / img_h, 1.0)  # 只缩小不放大
        if scale < 1.0:
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
            self.original_array = np.array(pil_img)
            img_w, img_h = new_w, new_h

        self.current_image = pil_img
        self.img_w, self.img_h = img_w, img_h
        self.input_w.set(self.img_w)
        self.input_h.set(self.img_h)
        self.scale_var.set(1.0)
        self.redraw_canvas()

    # 重绘画布
    def redraw_canvas(self):
        self.canvas.delete("all")
        if self.current_image is None: return
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        # 居中显示
        self.img_x = max((canvas_w - self.img_w) // 2, 0)
        self.img_y = max((canvas_h - self.img_h) // 2, 0)
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

    # 拖拽缩放
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
        # 保存历史
        self.undo_stack.append(self.current_image.copy())
        print(f"拖拽重采样: {int(self.img_w)} x {int(self.img_h)}，算法: {method}")
        new_arr = self.engine.process_image(self.original_array, self.img_w, self.img_h)
        self.current_image = Image.fromarray(new_arr)
        self.input_w.set(self.img_w)
        self.input_h.set(self.img_h)
        self.scale_var.set(self.img_w / self.original_array.shape[1])
        self.redraw_canvas()
        self.drag_data["type"] = None

    # 窗口输入区联动 
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

    # 应用窗口输入缩放
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
            # 保存历史
            self.undo_stack.append(self.current_image.copy())
            print(f"窗口输入重采样: {w} x {h}，插值算法: {method}")
            new_arr = self.engine.process_image(self.original_array, w, h)
            self.current_image = Image.fromarray(new_arr)
            self.img_w, self.img_h = w, h
            self.redraw_canvas()
        except Exception as e:
            messagebox.showerror("错误", f"输入有误: {e}")

    # 撤销 
    def undo(self):
        if self.undo_stack:
            self.current_image = self.undo_stack.pop()
            self.img_w, self.img_h = self.current_image.size
            self.input_w.set(self.img_w)
            self.input_h.set(self.img_h)
            self.scale_var.set(self.img_w / self.original_array.shape[1])
            self.redraw_canvas()
        else:
            messagebox.showinfo("提示", "没有可撤销的操作。")

    # 重置图片 
    def reset_image(self):
        if self.original_array is not None:
            pil_img = Image.fromarray(self.original_array)
            self.current_image = pil_img
            self.img_w, self.img_h = pil_img.size
            self.input_w.set(self.img_w)
            self.input_h.set(self.img_h)
            self.scale_var.set(1.0)
            self.undo_stack.clear()
            self.redraw_canvas()

    # 保存图片
    def save_image(self):
        if self.current_image is None:
            messagebox.showerror("错误", "没有图片可保存！")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg;*.jpeg"),
                ("BMP 图片", "*.bmp"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            return
        try:
            self.current_image.save(file_path)
            messagebox.showinfo("提示", f"图片已保存到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"错误信息: {e}")