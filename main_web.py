import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk

# ==========================================
# 1. 核心算法：手动实现的 Numpy 插值
#    (完全复用之前写的逻辑，符合大作业要求)
# ==========================================
class ManualInterpolationEngine:
    def _resize_axis0(self, src, new_len):
        old_len = src.shape[0]
        if new_len <= 0: return src
        scale = old_len / new_len
        u = (np.arange(new_len) + 0.5) * scale - 0.5
        u = np.clip(u, 0, old_len - 1)
        x = np.floor(u).astype(int)
        d = u - x
        x_next = np.clip(x + 1, 0, old_len - 1)
        shape_dims = [new_len] + [1] * (src.ndim - 1)
        d = d.reshape(shape_dims)
        return src[x] * (1 - d) + src[x_next] * d

    def process_image(self, img_arr, target_w, target_h):
        if img_arr is None: return None
        target_w, target_h = int(target_w), int(target_h)
        if target_w < 5 or target_h < 5: return img_arr # 最小限制
        
        # 移除 Alpha
        if img_arr.ndim == 3 and img_arr.shape[2] == 4:
            img_arr = img_arr[:, :, :3]

        img_transposed = img_arr.transpose(1, 0, 2)
        img_w_resized = self._resize_axis0(img_transposed, target_w)
        img_back = img_w_resized.transpose(1, 0, 2)
        final_img = self._resize_axis0(img_back, target_h)
        return np.clip(final_img, 0, 255).astype(np.uint8)

# ==========================================
# 2. Tkinter GUI：实现 PPT 式 8点拖拽
# ==========================================
class ResizableImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python大作业 - PPT式手动缩放")
        self.root.geometry("1000x800")
        
        self.engine = ManualInterpolationEngine()
        self.original_array = None # 存储高清原图(Numpy)
        self.current_image = None  # 当前显示的PIL图
        self.tk_image = None       # Tkinter显示的图
        
        # 布局
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="打开图片", command=self.load_image).pack(side=tk.LEFT, padx=10)
        tk.Label(btn_frame, text="操作提示：拖动红框的8个点来改变大小 -> 松手后触发算法缩放").pack(side=tk.LEFT, padx=10)
        
        # 画布
        self.canvas = tk.Canvas(root, bg="gray", width=900, height=700)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 状态变量
        self.img_x, self.img_y = 50, 50 # 图片位置
        self.img_w, self.img_h = 0, 0   # 当前显示大小
        
        self.drag_data = {"item": None, "x": 0, "y": 0, "type": None}
        
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not file_path: return
        
        # 加载图片
        pil_img = Image.open(file_path).convert("RGB")
        self.original_array = np.array(pil_img)
        self.current_image = pil_img
        self.img_w, self.img_h = pil_img.size
        
        self.redraw_canvas()

    def redraw_canvas(self):
        """重绘：图片 + 8个控制点"""
        self.canvas.delete("all")
        if self.current_image is None: return
        
        # 1. 绘制图片
        self.tk_image = ImageTk.PhotoImage(self.current_image)
        self.canvas.create_image(self.img_x, self.img_y, image=self.tk_image, anchor="nw", tags="image")
        
        # 2. 绘制边框 (红色虚线)
        x1, y1 = self.img_x, self.img_y
        x2, y2 = x1 + self.img_w, y1 + self.img_h
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", dash=(4, 4), tags="frame")
        
        # 3. 绘制 8 个控制点
        # 定义点的位置：(x, y, tag_name)
        mid_x, mid_y = x1 + self.img_w/2, y1 + self.img_h/2
        handles = [
            (x1, y1, "nw"), (mid_x, y1, "n"), (x2, y1, "ne"),   # 上三点
            (x2, mid_y, "e"), (x2, y2, "se"), (mid_x, y2, "s"), # 右、右下、下
            (x1, y2, "sw"), (x1, mid_y, "w")                    # 左下、左
        ]
        
        r = 5 # 控制点半径
        for hx, hy, tag in handles:
            # 绘制小方块，tag 标记它是哪个方向的点
            self.canvas.create_rectangle(hx-r, hy-r, hx+r, hy+r, fill="white", outline="black", tags=("handle", tag))

    def on_press(self, event):
        """鼠标按下：判断点到了哪个控制点"""
        # 获取点击的元素
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)
        
        if "handle" in tags:
            # 如果点到了控制点，记录是哪个方向 (nw, n, ne...)
            handle_type = [t for t in tags if t in ["nw","n","ne","e","se","s","sw","w"]][0]
            self.drag_data = {"item": item, "x": event.x, "y": event.y, "type": handle_type}
        elif "image" in tags:
            # 如果点到图片中间，则是移动图片
            self.drag_data = {"item": item, "x": event.x, "y": event.y, "type": "move"}
        else:
            self.drag_data = {"type": None}

    def on_drag(self, event):
        """鼠标拖动：实时更新红框大小 (为了流畅，此时不跑插值算法)"""
        if self.drag_data["type"] is None: return
        
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        handle = self.drag_data["type"]
        
        # 根据不同的手柄，调整 x, y, w, h
        if handle == "move":
            self.img_x += dx
            self.img_y += dy
        else:
            # 缩放逻辑
            if "e" in handle: self.img_w += dx
            if "w" in handle: self.img_x += dx; self.img_w -= dx
            if "s" in handle: self.img_h += dy
            if "n" in handle: self.img_y += dy; self.img_h -= dy
            
            # 最小尺寸保护
            if self.img_w < 10: self.img_w = 10
            if self.img_h < 10: self.img_h = 10

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        # 简单重绘框框（为了性能，这里我们只移动图片位置，不实时缩放图片像素）
        # 如果电脑性能好，也可以在这里实时调用 resize，但为了演示算法步骤，我们放在 release
        self.redraw_canvas()

    def on_release(self, event):
        """鼠标松开：执行算法，生成真正的高清图"""
        if self.drag_data["type"] is None: return
        
        # 如果只是移动位置，不需要重算像素
        if self.drag_data["type"] == "move":
            return

        # 核心：调用你自己写的算法
        print(f"触发重采样: 目标尺寸 {int(self.img_w)} x {int(self.img_h)}")
        
        # 调用手动插值引擎
        new_arr = self.engine.process_image(self.original_array, self.img_w, self.img_h)
        
        # 更新显示
        self.current_image = Image.fromarray(new_arr)
        self.redraw_canvas()
        self.drag_data["type"] = None

if __name__ == "__main__":
    root = tk.Tk()
    app = ResizableImageApp(root)
    root.mainloop()