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

    def _quadratic(self, p0, p1, p2, t):
        # Lagrange 二次插值
        return p0 * (t - 1) * t / 2 - p1 * (t + 1) * (t - 1) + p2 * (t + 1) * t / 2

    def _resize_biquadratic(self, img, new_w, new_h):
        src_h, src_w = img.shape[:2]
        dst = np.zeros((new_h, new_w, img.shape[2]), dtype=np.float32)
        x = np.linspace(0, src_w - 1, new_w)
        y = np.linspace(0, src_h - 1, new_h)
        for i, yy in enumerate(y):
            y0 = int(np.floor(yy))
            t_y = yy - y0
            y_indices = [max(y0 - 1, 0), y0, min(y0 + 1, src_h - 1)]
            for j, xx in enumerate(x):
                x0 = int(np.floor(xx))
                t_x = xx - x0
                x_indices = [max(x0 - 1, 0), x0, min(x0 + 1, src_w - 1)]
                patch = img[np.ix_(y_indices, x_indices)]
                # 先对x方向做二次插值
                col = np.array([self._quadratic(patch[k,0], patch[k,1], patch[k,2], t_x) for k in range(3)])
                # 再对y方向做二次插值
                dst[i, j] = self._quadratic(col[0], col[1], col[2], t_y)
        return np.clip(dst, 0, 255).astype(np.uint8)

    def _cubic(self, p0, p1, p2, p3, t):
        # Catmull-Rom 三次插值
        return (
            (-0.5*p0 + 1.5*p1 - 1.5*p2 + 0.5*p3) * t**3 +
            (p0 - 2.5*p1 + 2*p2 - 0.5*p3) * t**2 +
            (-0.5*p0 + 0.5*p2) * t +
            p1
        )

    def _resize_bicubic(self, img, new_w, new_h):
        src_h, src_w = img.shape[:2]
        dst = np.zeros((new_h, new_w, img.shape[2]), dtype=np.float32)
        x = np.linspace(0, src_w - 1, new_w)
        y = np.linspace(0, src_h - 1, new_h)
        for i, yy in enumerate(y):
            y0 = int(np.floor(yy))
            t_y = yy - y0
            # 取4个y索引，超出边界时用边界值
            y_indices = [np.clip(y0 + k, 0, src_h - 1) for k in [-1, 0, 1, 2]]
            for j, xx in enumerate(x):
                x0 = int(np.floor(xx))
                t_x = xx - x0
                # 取4个x索引，超出边界时用边界值
                x_indices = [np.clip(x0 + k, 0, src_w - 1) for k in [-1, 0, 1, 2]]
                # 取4x4邻域
                patch = img[np.ix_(y_indices, x_indices)]  # shape: (4,4,3)
                # 先对每一行做x方向三次插值
                inter_row = np.array([self._cubic(*patch[k, :, :], t_x) for k in range(4)])
                # 再对y方向做三次插值
                dst[i, j] = self._cubic(*inter_row, t_y)
        return np.clip(dst, 0, 255).astype(np.uint8)