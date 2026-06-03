"""从 win大师.png 精灵图中自动分帧，输出到 assets/sprites/ 目录"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
SOURCE_IMG = os.path.join(ASSETS_DIR, "win大师.png")
OUTPUT_DIR = os.path.join(ASSETS_DIR, "sprites")

# 动作定义：(名称, y起始, y结束, 帧切片起始索引, 帧数)
ACTIONS = [
    ("idle",      50,  240,  0,  5),   # 站立
    ("walk",      50,  240,  5,  11),  # 走路
    ("run",       250, 500,  0,  5),   # 跑步
    ("jump",      250, 500,  5,  10),  # 跳跃
    ("blink",     510, 740,  0,  6),   # 眨眼/表情
    ("talk",      510, 740,  6,  12),  # 讲话/表情
    ("special",   750, 990,  0,  9),   # 其他动作
]

# 动作的帧率 (fps)
ACTION_FPS = {
    "idle": 4,
    "walk": 8,
    "run": 10,
    "jump": 8,
    "blink": 6,
    "talk": 6,
    "special": 4,
}


def get_density(pixels, y1, y2, x1, x2, img_h):
    """获取区域每列的非透明像素密度"""
    result = []
    for x in range(x1, x2 + 1):
        count = 0
        for y in range(y1, min(y2, img_h)):
            if pixels[x, y][3] > 10:
                count += 1
        result.append(count)
    return result


def find_best_split(pixels, y1, y2, x1, x2, img_h):
    """在宽段中找到最佳分割点（密度最低处）"""
    densities = get_density(pixels, y1, y2, x1, x2, img_h)
    total_w = len(densities)
    search_start = max(10, int(total_w * 0.15))
    search_end = min(total_w - 10, int(total_w * 0.85))

    best_x = -1
    best_score = 999999
    for i in range(search_start, search_end):
        local_avg = sum(densities[max(0, i - 3):i + 4]) / 7
        if local_avg < best_score:
            best_score = local_avg
            best_x = i

    return (x1 + best_x, best_score) if best_score < 50 else (-1, 0)


def split_wide_segment(pixels, y1, y2, seg, img_h, max_w=180):
    """递归分割宽段"""
    parts = [seg]
    while True:
        new_parts = []
        did_split = False
        for p in parts:
            pw = p[1] - p[0] + 1
            if pw > max_w:
                split_x, score = find_best_split(pixels, y1, y2, p[0], p[1], img_h)
                if split_x > 0:
                    new_parts.append((p[0], split_x - 1))
                    new_parts.append((split_x, p[1]))
                    did_split = True
                else:
                    new_parts.append(p)
            else:
                new_parts.append(p)
        parts = new_parts
        if not did_split:
            break
    return parts


def extract_row_segments(pixels, y1, y2, img_w, img_h):
    """提取一行中的所有帧段"""
    col_active = []
    for x in range(img_w):
        count = sum(1 for y in range(y1, min(y2, img_h)) if pixels[x, y][3] > 10)
        col_active.append(count > 3)

    segments = []
    seg_start = None
    last_active = None
    gap = 0
    for x in range(img_w):
        if col_active[x]:
            if seg_start is None:
                seg_start = x
            last_active = x
            gap = 0
        else:
            if seg_start is not None:
                gap += 1
                if gap > 3:
                    if last_active - seg_start + 1 >= 30:
                        segments.append((seg_start, last_active))
                    seg_start = last_active = None
                    gap = 0
    if seg_start is not None and last_active is not None:
        if last_active - seg_start + 1 >= 30:
            segments.append((seg_start, last_active))

    # 对宽段递归分割
    result = []
    for seg in segments:
        result.extend(split_wide_segment(pixels, y1, y2, seg, img_h))
    return result


def _trim_black_border(img):
    """裁剪图片边缘的黑色边框（原精灵图矩形框残留）。
    
    从四边向内扫描，逐行/列检测深色像素占比。
    只要边缘行列的深色占比>30%就继续裁剪，直到遇到正常内容。
    """
    px = img.load()
    w, h = img.size
    if w < 10 or h < 10:
        return img

    def dark_ratio_row(y):
        """返回行的深色像素占比"""
        dark = 0
        total = 0
        for x in range(w):
            if px[x, y][3] > 10:
                total += 1
                if (px[x, y][0] + px[x, y][1] + px[x, y][2]) / 3 < 60:
                    dark += 1
        return dark / max(total, 1)

    def dark_ratio_col(x):
        """返回列的深色像素占比"""
        dark = 0
        total = 0
        for y in range(h):
            if px[x, y][3] > 10:
                total += 1
                if (px[x, y][0] + px[x, y][1] + px[x, y][2]) / 3 < 60:
                    dark += 1
        return dark / max(total, 1)

    # 从上往下裁（深色占比>30%的行视为边框）
    top = 0
    for y in range(h):
        if dark_ratio_row(y) > 0.30:
            top = y + 1
        else:
            break

    # 从下往上裁
    bottom = h - 1
    for y in range(h - 1, -1, -1):
        if dark_ratio_row(y) > 0.30:
            bottom = y - 1
        else:
            break

    # 从左往右裁
    left = 0
    for x in range(w):
        if dark_ratio_col(x) > 0.30:
            left = x + 1
        else:
            break

    # 从右往左裁
    right = w - 1
    for x in range(w - 1, -1, -1):
        if dark_ratio_col(x) > 0.30:
            right = x - 1
        else:
            break

    if left >= right or top >= bottom:
        return img

    cropped = img.crop((left, top, right + 1, bottom + 1))
    if cropped.size[0] < 10 or cropped.size[1] < 10:
        return img
    return cropped


def main():
    img = Image.open(SOURCE_IMG).convert("RGBA")
    pixels = img.load()
    img_w, img_h = img.size
    print(f"源图: {SOURCE_IMG} ({img_w}x{img_h})")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 按行提取所有段
    row_cache = {}
    total_extracted = 0

    for action_name, y1, y2, idx_start, idx_end in ACTIONS:
        if y1 not in row_cache:
            row_cache[y1] = extract_row_segments(pixels, y1, y2, img_w, img_h)

        frames = row_cache[y1][idx_start:idx_end]
        expected = idx_end - idx_start

        # 创建动作子目录
        action_dir = os.path.join(OUTPUT_DIR, action_name)
        os.makedirs(action_dir, exist_ok=True)

        # 裁切并保存每帧
        for i, (x1, x2) in enumerate(frames):
            # 在行范围内找实际内容的上下边界
            frame_y1, frame_y2 = y1, y2
            # 裁切（保留透明背景）
            cropped = img.crop((x1, frame_y1, x2 + 1, frame_y2 + 1))

            # 自动裁剪透明边缘
            bbox = cropped.getbbox()
            if bbox:
                cropped = cropped.crop(bbox)

            # 裁剪黑色边框（原精灵图的黑色矩形框残留）
            cropped = _trim_black_border(cropped)
            # 再做一次透明裁切，清除边框裁切后可能残留的空白
            bbox2 = cropped.getbbox()
            if bbox2:
                cropped = cropped.crop(bbox2)

            filename = f"{i:03d}.png"
            filepath = os.path.join(action_dir, filename)
            cropped.save(filepath)
            total_extracted += 1

        print(f"  {action_name}: {len(frames)}/{expected}帧 -> {action_dir}/")

    # 保存动作元数据
    meta_path = os.path.join(OUTPUT_DIR, "actions.json")
    import json
    meta = {}
    for action_name, y1, y2, idx_start, idx_end in ACTIONS:
        frames = row_cache[y1][idx_start:idx_end]
        meta[action_name] = {
            "frame_count": len(frames),
            "fps": ACTION_FPS[action_name],
            "frames": [f"{i:03d}.png" for i in range(len(frames))],
        }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"\n完成！共提取 {total_extracted} 帧 -> {OUTPUT_DIR}/")
    print(f"元数据 -> {meta_path}")


if __name__ == "__main__":
    main()
