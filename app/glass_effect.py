"""Windows 毛玻璃效果工具 — 使用 DWM API 实现真正的背景模糊

用法:
    from .glass_effect import apply_acrylic_effect, remove_acrylic_effect
    
    # 对 QWidget 应用毛玻璃
    apply_acrylic_effect(widget)
    
    # 移除效果
    remove_acrylic_effect(widget)
"""

import sys
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QWidget

# Windows DWM API 常量
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_MICA_EFFECT = 39

# 背景类型
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2  # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
DWMSBT_TABBEDWINDOW = 4  # Tabbed Mica

# 模糊常量
ACCENT_DISABLED = 0
ACCENT_ENABLE_GRADIENT = 1
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_ACRYLICBLURBEHIND = 3
ACCENT_ENABLE_HOSTBACKDROP = 5

# 窗口组合常量
WCA_ACCENT_POLICY = 19

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("pvData", ctypes.POINTER(ACCENT_POLICY)),
        ("cbData", ctypes.c_size_t),
    ]

# 加载 Windows API
if sys.platform == 'win32':
    try:
        user32 = ctypes.windll.user32
        dwmapi = ctypes.windll.dwmapi
        
        # 设置窗口组合属性
        SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
        SetWindowCompositionAttribute.restype = wintypes.BOOL
        SetWindowCompositionAttribute.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA),
        ]
        
        # DWM 设置窗口属性
        DwmSetWindowAttribute = dwmapi.DwmSetWindowAttribute
        DwmSetWindowAttribute.restype = ctypes.c_int
        DwmSetWindowAttribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_int),
            wintypes.DWORD,
        ]
        
        _HAS_DWM = True
    except Exception:
        _HAS_DWM = False
else:
    _HAS_DWM = False


def apply_acrylic_effect(widget: QWidget, tint_color: int = 0x01000000):
    """应用 Acrylic 毛玻璃效果（Windows 10/11）
    
    Args:
        widget: 目标 QWidget
        tint_color: 着色颜色 (AARRGGBB 格式)，默认几乎透明
    """
    if not _HAS_DWM:
        return False
    
    try:
        hwnd = int(widget.winId())
        
        # 设置 Acrylic 模糊效果
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.GradientColor = tint_color  # 半透明黑色着色
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.pvData = ctypes.pointer(accent)
        data.cbData = ctypes.sizeof(accent)
        
        result = SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
        return bool(result)
    except Exception as e:
        print(f"[Glass] Acrylic 效果应用失败: {e}")
        return False


def apply_mica_effect(widget: QWidget, dark_mode: bool = False):
    """应用 Mica 效果（Windows 11）
    
    Args:
        widget: 目标 QWidget
        dark_mode: 是否使用深色模式
    """
    if not _HAS_DWM:
        return False
    
    try:
        hwnd = int(widget.winId())
        
        # 设置深色模式
        if dark_mode:
            value = ctypes.c_int(1)
            DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.pointer(value),
                ctypes.sizeof(value)
            )
        
        # 设置 Mica 背景类型
        backdrop_type = ctypes.c_int(DWMSBT_MAINWINDOW)
        result = DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.pointer(backdrop_type),
            ctypes.sizeof(backdrop_type)
        )
        
        return result == 0  # S_OK = 0
    except Exception as e:
        print(f"[Glass] Mica 效果应用失败: {e}")
        return False


def apply_blur_behind(widget: QWidget, opacity: int = 0x80):
    """应用传统模糊效果（Windows 7/8/10/11）
    
    Args:
        widget: 目标 QWidget
        opacity: 不透明度 (0-255)
    """
    if not _HAS_DWM:
        return False
    
    try:
        hwnd = int(widget.winId())
        
        # 使用半透明渐变实现模糊
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT
        accent.GradientColor = (opacity << 24)  # 半透明黑色
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.pvData = ctypes.pointer(accent)
        data.cbData = ctypes.sizeof(accent)
        
        result = SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
        return bool(result)
    except Exception as e:
        print(f"[Glass] 模糊效果应用失败: {e}")
        return False


def remove_effects(widget: QWidget):
    """移除所有毛玻璃效果"""
    if not _HAS_DWM:
        return
    
    try:
        hwnd = int(widget.winId())
        
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_DISABLED
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.pvData = ctypes.pointer(accent)
        data.cbData = ctypes.sizeof(accent)
        
        SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
    except Exception as e:
        print(f"[Glass] 移除效果失败: {e}")


def is_available() -> bool:
    """检查是否支持毛玻璃效果"""
    return _HAS_DWM
