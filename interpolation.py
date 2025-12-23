import numpy as np

# ==========================================
# 1. 核心算法：手动实现的 Numpy 插值
#    (完全复用之前写的逻辑，符合大作业要求)
# ==========================================
class ManualInterpolationEngine:
    def __init__(self, method="bilinear"):
        self.method = method

    def set_method(self, method):
        self.method = method

    def process_image(self, img_arr, target_w, target_h):
        if img_arr is None: return None
        target_w, target_h = int(target_w), int(target_h)
        if target_w < 5 or target_h < 5: return img_arr # 最小限制
        
        # 移除 Alpha
        if img_arr.ndim == 3 and img_arr.shape[2] == 4:
            img_arr = img_arr[:, :, :3]

        if self.method == "nearest":
            return self._resize_nearest(img_arr, target_w, target_h)
        elif self.method == "bilinear":
            return self._resize_bilinear(img_arr, target_w, target_h)
        elif self.method == "biquadratic":
            return self._resize_biquadratic(img_arr, target_w, target_h)
        elif self.method == "bicubic":
            return self._resize_bicubic(img_arr, target_w, target_h)
        else:
            return self._resize_bilinear(img_arr, target_w, target_h)

    def _resize_nearest(self, img, new_w, new_h):
        src_h, src_w = img.shape[:2]
        y_idx = (np.arange(new_h) * src_h / new_h).astype(int)
        x_idx = (np.arange(new_w) * src_w / new_w).astype(int)
        y_idx = np.clip(y_idx, 0, src_h-1)
        x_idx = np.clip(x_idx, 0, src_w-1)
        return img[y_idx][:, x_idx]

    def _resize_bilinear(self, img, new_w, new_h):
        # 向量化实现
        src_h, src_w = img.shape[:2]
        if new_h == 1:
            y = np.zeros((1,))
        else:
            y = np.linspace(0, src_h - 1, new_h)
        if new_w == 1:
            x = np.zeros((1,))
        else:
            x = np.linspace(0, src_w - 1, new_w)
        x_floor = np.floor(x).astype(int)
        y_floor = np.floor(y).astype(int)
        x_ceil = np.clip(x_floor + 1, 0, src_w - 1)
        y_ceil = np.clip(y_floor + 1, 0, src_h - 1)
        x_weight = x - x_floor
        y_weight = y - y_floor

        # meshgrid
        xx, yy = np.meshgrid(x_floor, y_floor)
        xx1, yy1 = np.meshgrid(x_ceil, y_floor)
        xx2, yy2 = np.meshgrid(x_floor, y_ceil)
        xx3, yy3 = np.meshgrid(x_ceil, y_ceil)

        wa = (1 - x_weight)[None, :] * (1 - y_weight)[:, None]
        wb = x_weight[None, :] * (1 - y_weight)[:, None]
        wc = (1 - x_weight)[None, :] * y_weight[:, None]
        wd = x_weight[None, :] * y_weight[:, None]

        a = img[yy, xx]
        b = img[yy1, xx1]
        c = img[yy2, xx2]
        d = img[yy3, xx3]

        dst = wa[..., None] * a + wb[..., None] * b + wc[..., None] * c + wd[..., None] * d
        return np.clip(dst, 0, 255).astype(np.uint8)

    def _resize_biquadratic(self, img, new_w, new_h):
        # 二次插值向量化较难，这里仍用循环，但只对目标像素点循环
        def quadratic_interp(p0, p1, p2, t):
            return p1 + 0.5 * t * (p2 - p0 + t * (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p0 + t * (3.0 * (p1 - p2) + p0 - p2)))
        src_h, src_w = img.shape[:2]
        dst = np.zeros((new_h, new_w, img.shape[2]), dtype=np.float32)
        x = np.linspace(0, src_w - 1, new_w)
        y = np.linspace(0, src_h - 1, new_h)
        for i, yy in enumerate(y):
            y0 = int(np.floor(yy))
            y1 = min(y0 + 1, src_h - 1)
            y_ = yy - y0
            y0m = max(y0 - 1, 0)
            y2 = min(y0 + 2, src_h - 1)
            for j, xx in enumerate(x):
                x0 = int(np.floor(xx))
                x1 = min(x0 + 1, src_w - 1)
                x_ = xx - x0
                x0m = max(x0 - 1, 0)
                x2 = min(x0 + 2, src_w - 1)
                col = np.zeros((3, img.shape[2]))
                col[0] = quadratic_interp(img[y0m, x0], img[y0, x0], img[y1, x0], y_)
                col[1] = quadratic_interp(img[y0m, x1], img[y0, x1], img[y1, x1], y_)
                col[2] = quadratic_interp(img[y0m, x2], img[y0, x2], img[y1, x2], y_)
                dst[i, j] = quadratic_interp(col[0], col[1], col[2], x_)
        return np.clip(dst, 0, 255).astype(np.uint8)

    def _cubic(self, a, b, c, d, t):
        return (
            (-0.5*a + 1.5*b - 1.5*c + 0.5*d) * t**3 +
            (a - 2.5*b + 2*c - 0.5*d) * t**2 +
            (-0.5*a + 0.5*c) * t +
            b
        )

    def _resize_bicubic(self, img, new_w, new_h):
        # 仍然是逐点，但只循环目标像素点，已较快
        src_h, src_w = img.shape[:2]
        dst = np.zeros((new_h, new_w, img.shape[2]), dtype=np.float32)
        x = np.linspace(0, src_w - 1, new_w)
        y = np.linspace(0, src_h - 1, new_h)
        for i, yy in enumerate(y):
            y_int = int(np.floor(yy))
            y_ = yy - y_int
            y_indices = [min(max(y_int + n, 0), src_h - 1) for n in [-1, 0, 1, 2]]
            for j, xx in enumerate(x):
                x_int = int(np.floor(xx))
                x_ = xx - x_int
                x_indices = [min(max(x_int + n, 0), src_w - 1) for n in [-1, 0, 1, 2]]
                patch = img[np.ix_(y_indices, x_indices)]
                col = np.zeros((4, img.shape[2]))
                for k in range(4):
                    col[k] = self._cubic(*patch[k], x_)
                dst[i, j] = self._cubic(*col, y_)
        return np.clip(dst, 0, 255).astype(np.uint8)