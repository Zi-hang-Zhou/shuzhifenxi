import numpy as np

class InterpolationEngine:
    def __init__(self, method="bilinear"):
        self.method = method

    def set_method(self, method):
        self.method = method

    def process_image(self, img_arr, target_w, target_h):
        if img_arr is None: return None
        target_w, target_h = int(target_w), int(target_h)
        # 最小限制
        if target_w < 5 or target_h < 5: return img_arr 
        # 确保处理的是RGB三通道图片
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
        old_h, old_w = img.shape[:2]
        h = (np.arange(new_h) * old_h / new_h).astype(int)
        w = (np.arange(new_w) * old_w / new_w).astype(int)
        h = np.clip(h, 0, old_h-1)
        w = np.clip(w, 0, old_w-1)
        return img[h][:, w]
    
    def _resize_1d_bilinear(self, img, new_size, axis):
        old_len = img.shape[axis]
        x_new = np.linspace(0, old_len - 1, new_size)
        x0 = np.floor(x_new).astype(np.int32)
        x1 = np.clip(x0 + 1, 0, old_len - 1)
        t = x_new - x0

        if axis == 0:  # 垂直方向
            f0 = img[x0, :, :]
            f1 = img[x1, :, :]
            t = t[:, None, None]
            result = (1 - t) * f0 + t * f1
        else:  # 水平方向
            f0 = img[:, x0, :]
            f1 = img[:, x1, :]
            t = t[None, :, None]
            result = (1 - t) * f0 + t * f1
        return result

    def _resize_bilinear(self, img, new_w, new_h):
        # 先水平方向插值
        img_after_h = self._resize_1d_bilinear(img, new_w, axis=1)
        # 再垂直方向插值
        img_final = self._resize_1d_bilinear(img_after_h, new_h, axis=0)
        return np.clip(img_final, 0, 255).astype(np.uint8)

    def _get_biquadratic_weights(self, t):  # t为插值点和取整后的结果之差
        w0 = 0.5 * t * (t - 1)
        w1 = -(t + 1) * (t - 1)
        w2 = 0.5 * t * (t + 1)
        return np.stack([w0, w1, w2], axis=1)

    def _resize_1d_biquadratic(self, img, new_size, axis):
        old_len = img.shape[axis]
        x_new = np.linspace(0, old_len - 1, new_size)
        x0 = np.floor(x_new).astype(np.int32)
        t = x_new - x0
        
        indices = np.stack([x0 - 1, x0, x0 + 1], axis=1)
        indices = np.clip(indices, 0, old_len - 1)
        
        weights = self._get_biquadratic_weights(t)
        
        if axis == 0: # 垂直方向
            f = img[indices, :, :] 
            weights = weights[:, :, None, None]
            result = np.sum(f * weights, axis=1)
        else: # 水平方向
            f = img[:, indices, :] 
            weights = weights[None, :, :, None]
            result = np.sum(f * weights, axis=2)
        return result

    def _resize_biquadratic(self, img, new_w, new_h):
        # 先水平方向插值
        img_after_h = self._resize_1d_biquadratic(img, new_w, axis=1)
        # 再垂直方向插值
        img_final = self._resize_1d_biquadratic(img_after_h, new_h, axis=0)
        return np.clip(img_final, 0, 255).astype(np.uint8)

    def _get_bicubic_weights(self, t):  # t为插值点和取整后的结果之差
        w0 = - t * (t - 1) * (t - 2) / 6
        w1 = (t + 1) * (t - 1) * (t - 2) / 2
        w2 = - (t + 1) * t * (t - 2) / 2
        w3 = (t + 1) * t * (t - 1) / 6
        return np.stack([w0, w1, w2, w3], axis=1)

    def _resize_1d_bicubic(self, img, new_size, axis):
        old_len = img.shape[axis]
        x_new = np.linspace(0, old_len - 1, new_size)
    
        x0 = np.floor(x_new).astype(np.int32)
        t = x_new - x0
        
        indices = np.stack([x0 - 1, x0, x0 + 1, x0 + 2], axis=1)
        indices = np.clip(indices, 0, old_len - 1)
        
        weights = self._get_bicubic_weights(t)
        
        if axis == 0:  # 垂直方向
            f = img[indices, :, :] 
            weights = weights[:, :, None, None]
            result = np.sum(f * weights, axis=1)
        else:  # 水平
            f = img[:, indices, :]
            weights = weights[None, :, :, None]
            result = np.sum(f * weights, axis=2)
        return result

    def _resize_bicubic(self, img, new_w, new_h):
        # 先水平方向插值
        temp_img = self._resize_1d_bicubic(img, new_w, axis=1)
        # 再垂直方向插值
        dst = self._resize_1d_bicubic(temp_img, new_h, axis=0)
        return np.clip(dst, 0, 255).astype(np.uint8)

    