import numpy as np
import matplotlib.pyplot as plt
from interpolation import InterpolationEngine
from PIL import Image, ImageDraw
import os
import tkinter as tk
from tkinter import filedialog

plt.rcParams['axes.unicode_minus'] = False 
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial']

class FloatInterpolationEngine(InterpolationEngine):

    def _resize_bilinear(self, img, new_w, new_h):
        img_after_h = self._resize_1d_bilinear(img, new_w, axis=1)
        img_final = self._resize_1d_bilinear(img_after_h, new_h, axis=0)
        return img_final 

    def _resize_biquadratic(self, img, new_w, new_h):
        img_after_h = self._resize_1d_biquadratic(img, new_w, axis=1)
        img_final = self._resize_1d_biquadratic(img_after_h, new_h, axis=0)
        return img_final 

    def _resize_bicubic(self, img, new_w, new_h):
        temp_img = self._resize_1d_bicubic(img, new_w, axis=1)
        dst = self._resize_1d_bicubic(temp_img, new_h, axis=0)
        return dst

def get_user_image():

    try:
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(title="选择测试图片", filetypes=[("Images", "*.png *.jpg")])
        root.destroy()
        if file_path: return Image.open(file_path).convert("RGB")
    except: pass
    img = Image.new('RGB', (256, 256), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill='blue', outline='black')
    return img

def run_final_validation():
    if not os.path.exists("results_final"): os.makedirs("results_final")
    float_engine = FloatInterpolationEngine() 
    methods = ["nearest", "bilinear", "biquadratic", "bicubic"]


   # 实验 1: 数值精确性验证
    print("f(x,y) = 123.45")
    img_const = np.full((10, 10, 1), 123.45, dtype=float)
    for m in methods:
        float_engine.set_method(m)
        res = float_engine.process_image(img_const, 30, 30)
        max_diff = np.max(np.abs(res - 123.45))
        judge = "PASS" if max_diff < 1e-9 else "FAIL"
        print(f"  {m:<12} | Max Diff: {max_diff:.2e} | {judge}")

    print("f(x,y) = 2x + 3y + 10")
    h_in, w_in = 10, 10
    target_w, target_h = 55, 55 

    def plane_func(x, y): return 2.0 * x + 3.0 * y + 10.0

    y_idx_in, x_idx_in = np.mgrid[0:h_in, 0:w_in].astype(float)
    z_in = plane_func(x_idx_in, y_idx_in)
    img_plane = np.stack([z_in]*3, axis=-1)

    gt_x_coords = np.linspace(0, w_in - 1, target_w)
    gt_y_coords = np.linspace(0, h_in - 1, target_h)
    gt_xx, gt_yy = np.meshgrid(gt_x_coords, gt_y_coords) 
    z_gt = plane_func(gt_xx, gt_yy)
    print(f"{'Method':<12} | {'RMSE (Float)':<15} | {'Conclusion'}")
    for m in methods:
        float_engine.set_method(m)
        res = float_engine.process_image(img_plane, target_w, target_h)
        
        diff = res[:, :, 0] - z_gt
        rmse = np.sqrt(np.mean(diff**2))
        
        judge = ""
        if m == "bilinear":
            if rmse < 1e-10: judge = "PERFECT (Math Exact)"
            else: judge = "Error?"
        elif m == "nearest":
            judge = "High Error (Expected)"
        
        print(f"{m:<12} | {rmse:<15.4e} | {judge}")



    h_lr, w_lr = 8, 8
    target_w_hr, target_h_hr = 64, 64


    def gauss_func(x, y):
        cx, cy = (w_lr-1)/2.0, (h_lr-1)/2.0
        sigma = 1.5
        return 100.0 * np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))

    y_in, x_in = np.mgrid[0:h_lr, 0:w_lr].astype(float)
    z_in_gauss = gauss_func(x_in, y_in)
    img_gauss = np.stack([z_in_gauss]*3, axis=-1)

    gt_x_gauss = np.linspace(0, w_lr - 1, target_w_hr)
    gt_y_gauss = np.linspace(0, h_lr - 1, target_h_hr)
    xx_gauss, yy_gauss = np.meshgrid(gt_x_gauss, gt_y_gauss)
    z_gt_gauss = gauss_func(xx_gauss, yy_gauss)

    print(f"{'Method':<12} | {'RMSE':<15} | {'Relative Error'}")

    results = {}
    for m in methods:
        float_engine.set_method(m)
        res = float_engine.process_image(img_gauss, target_w_hr, target_h_hr)
        
        diff = res[:, :, 0] - z_gt_gauss
        rmse = np.sqrt(np.mean(diff**2))
        results[m] = rmse
        
        print(f"{m:<12} | {rmse:<15.4f} | {(rmse/100)*100:.2f}%")
    



    # 实验 2: 阶跃响应分析
    width = 20
    img_edge = np.zeros((1, width, 3), dtype=float)
    img_edge[:, :width//2, :] = 50.0  
    img_edge[:, width//2:, :] = 200.0 
    
    target_w_edge = 400 
    
    plt.figure(figsize=(10, 6), dpi=120)
    colors = {"nearest": "green", "bilinear": "blue", "biquadratic": "orange", "bicubic": "red"}
    styles = {"nearest": "--", "bilinear": "-.", "biquadratic": "-", "bicubic": "-"}

    for m in methods:
        float_engine.set_method(m)
        if m == "nearest": res = float_engine._resize_nearest(img_edge, target_w_edge, 1)
        elif m == "bilinear": res = float_engine._resize_bilinear(img_edge, target_w_edge, 1)
        elif m == "biquadratic": res = float_engine._resize_biquadratic(img_edge, target_w_edge, 1)
        elif m == "bicubic": res = float_engine._resize_bicubic(img_edge, target_w_edge, 1)
        
        x_axis = np.linspace(0, width, target_w_edge)
        plt.plot(x_axis, res[0, :, 0], label=m.capitalize(), color=colors[m], linestyle=styles[m], linewidth=2)

    plt.title("Edge Step Response Analysis", fontsize=14)
    plt.xlabel("Spatial Position", fontsize=12)
    plt.ylabel("Pixel Intensity", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.xlim(width/2 - 2, width/2 + 2) 
    plt.tight_layout()
    plt.savefig("results_final/edge_response.png")


    # 实验 3: 图像评估
    real_engine = FloatInterpolationEngine()

    img = get_user_image()
    img_arr = np.array(img, dtype=float)
    h, w = img_arr.shape[:2]
    if w > 800: 
        img = img.resize((w//2, h//2))
        img_arr = np.array(img, dtype=float)
        h, w = img_arr.shape[:2]

    real_engine.set_method("bilinear")
    small_real = real_engine.process_image(img_arr, w//2, h//2)
    
    results = []
    print(f"{'Rank':<5} | {'Algorithm':<15} | {'PSNR (dB)':<15}")
    print("-" * 45)
    
    for m in methods:
        real_engine.set_method(m)
        rec = real_engine.process_image(small_real, w, h)
        mse = np.mean((img_arr - rec) ** 2)
        if mse == 0:
            psnr = 100.0 
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        results.append((m, psnr))
    results.sort(key=lambda x: x[1], reverse=True)
    for i, (m, score) in enumerate(results):
        print(f"{i+1:<5} | {m:<15} | {score:<15.2f}")

if __name__ == "__main__":
    run_final_validation()
