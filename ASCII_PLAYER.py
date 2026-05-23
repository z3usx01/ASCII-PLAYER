"""
ASCII Player Video Creator 
====================================================
Features:
  - Fast Startup with minimal interface
  - MP4 Export with frame management
  - High density rendering with extended palette
  - Auto/Manual aspect ratio adjustment

Credits: z3usx01 , johan_cicada
License: MIT (Open Source)
=====================================================
"""

import cv2
import os
import sys
import time
import threading
import shutil
import numpy as np
from queue import Queue
from PIL import Image, ImageDraw, ImageFont


T = {
    "app_name": "ASCII Player Video Creator",
    "input_path": "Enter video path: ",
    "enable_color": "Character color? (y/N): ",
    "output_width": "Output width (blank for Auto, terminal={}): ",
    "skip_n_frames": "Skip every N frames (default 1): ",
    "repeat_video": "Preview in loop? (y/N): ",
    "playback_finished": "Playback finished.",
    "export_q": "Do you want to export it as MP4? (y/N): ",
    "export_folder": "Create a temp folder, copy its path and paste it here: ",
    "export_mode_q": "What to keep? (1. Only MP4 video | 2. Video + Each PNG frame): ",
    "export_bg": "Background color (1. Black | 2. White | 3. Blue | 4. Custom Hex): ",
    "export_start": "Creating video... Please wait.",
    "export_done": "Video finished! Saved at: ",
    "cleaning_temp": "Deleting temporary frames folder...",
    "try_again_q": "Do you want to try another video? (y/N): ",
    "stopped_user": "Stopped.",
    "error_not_found": "File not found: '{}'",
    "error_open": "Could not open video.",
    "processing_frame": "Frame {}/{}..."
}

def show_logo():
    clear_console()
    logo = f"""
{C_CYAN}    █████╗ ███████╗ ██████╗██╗██╗    ██████╗ ██╗      █████╗ ██╗   ██╗███████╗██████╗ 
{C_CYAN}   ██╔══██╗██╔════╝██╔════╝██║██║    ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗
{C_CYAN}   ███████║███████╗██║     ██║██║    ██████╔╝██║     ███████║ ╚████╔╝ █████╗  ██████╔╝
{C_CYAN}   ██╔══██║╚════██║██║     ██║██║    ██╔═══╝ ██║     ██╔══██║  ╚██╔╝  ██╔══╝  ██╔══██╗
{C_CYAN}   ██║  ██║███████║╚██████╗██║██║    ██║     ███████╗██║  ██║   ██║   ███████╗██║  ██║
{C_CYAN}   ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝{RESET_COLOR}
    """
    print(logo)

# ── Extended Character Set ────────────────────────────────────────────────────
ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczmwqpdbkhao*#MW&8%B@$0QSXGZJKPHDAUYTRENVLCF"
_CHARS_ARRAY = np.array(list(ASCII_CHARS))

# ── ANSI Escape Codes & Colors ────────────────────────────────────────────────
CURSOR_HOME  = "\033[H"
CLEAR_SCREEN = "\033[2J"
HIDE_CURSOR  = "\033[?25l"
SHOW_CURSOR  = "\033[?25h"
RESET_COLOR  = "\033[0m"

C_CYAN   = "\033[96m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_RED    = "\033[91m"
C_GRAY   = "\033[90m"
C_BOLD   = "\033[1m"

def clear_console():
    if os.name == "nt": os.system("cls")
    else: os.system("clear")

def enable_ansi_windows() -> None:
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception: pass

def get_video_info(cap: cv2.VideoCapture) -> dict:
    return {
        "fps"          : cap.get(cv2.CAP_PROP_FPS),
        "total_frames" : int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width_px"     : int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height_px"    : int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "duration_s"   : cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
    }

# ── Conversion & Rendering ────────────────────────────────────────────────────

def frame_to_ascii_nocolor(frame, width: int) -> str:
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized = cv2.resize(frame, (width, height))
    gray    = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    n_chars = len(ASCII_CHARS) - 1
    lines = []
    for row in gray:
        line = "".join(ASCII_CHARS[int(p / 255.0 * n_chars)] for p in row)
        lines.append(line)
    return "\n".join(lines)

def frame_to_ascii_color(frame, width: int) -> tuple:
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized     = cv2.resize(frame, (width, height))
    resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    brightness   = 0.299 * resized_rgb[:,:,0] + 0.587 * resized_rgb[:,:,1] + 0.114 * resized_rgb[:,:,2]
    char_indices = np.clip((brightness / 255.0 * (len(ASCII_CHARS) - 1)).astype(np.int32), 0, len(ASCII_CHARS) - 1)
    return _CHARS_ARRAY[char_indices], resized_rgb

def ascii_to_image(char_map, rgb_map, bg_color, font_size=10):
    h, w = char_map.shape
    char_w, char_h = font_size * 0.6, font_size
    img = Image.new("RGB", (int(w * char_w), int(h * char_h)), bg_color)
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("consola.ttf", font_size)
    except:
        try: font = ImageFont.truetype("cour.ttf", font_size)
        except: font = ImageFont.load_default()
    for y in range(h):
        for x in range(w):
            color = tuple(rgb_map[y, x]) if rgb_map is not None else (255, 255, 255)
            draw.text((x * char_w, y * char_h), char_map[y, x], fill=color, font=font)
    return img

# ── Export Flow ───────────────────────────────────────────────────────────────

def export_flow(video_path, use_color, width):
    clear_console()
    print(f"\n  {C_BOLD}{C_GREEN}» MP4 EXPORT «{RESET_COLOR}")
    folder = input(f"\n  {T['export_folder']}").strip().strip('"')
    if not folder: return
    
    keep_mode = input(f"\n  {T['export_mode_q']}").strip()
    bg_choice = input(f"\n  {T['export_bg']}").strip()
    
    bg_color = (0, 0, 0)
    if bg_choice == "2": bg_color = (255, 255, 255)
    elif bg_choice == "3": bg_color = (0, 0, 255)
    elif bg_choice == "4":
        hex_c = input("  Hex (#RRGGBB): ").strip().lstrip("#")
        bg_color = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
    
    temp_dir = os.path.join(folder, "temp_ascii_frames")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    cap = cv2.VideoCapture(video_path)
    info = get_video_info(cap)
    total, fps = info["total_frames"], info["fps"]
    
    print(f"\n  {C_YELLOW}{T['export_start']}{RESET_COLOR}")
    
    for i in range(1, total + 1):
        ret, frame = cap.read()
        if not ret: break
        if use_color: char_map, rgb_map = frame_to_ascii_color(frame, width)
        else:
            txt = frame_to_ascii_nocolor(frame, width)
            char_map = np.array([list(l) for l in txt.split("\n")])
            rgb_map = None
        img = ascii_to_image(char_map, rgb_map, bg_color)
        img.save(os.path.join(temp_dir, f"f_{i:05d}.png"))
        if i % 10 == 0: sys.stdout.write(f"\r  {T['processing_frame'].format(i, total)}"); sys.stdout.flush()
    
    cap.release()
    output_v = os.path.join(folder, "ASCII_Player_Output.mp4")
    sample = cv2.imread(os.path.join(temp_dir, "f_00001.png"))
    out = cv2.VideoWriter(output_v, cv2.VideoWriter_fourcc(*'mp4v'), fps, (sample.shape[1], sample.shape[0]))
    for i in range(1, total + 1):
        out.write(cv2.imread(os.path.join(temp_dir, f"f_{i:05d}.png")))
    out.release()
    
    if keep_mode == "1":
        print(f"\n  {C_GRAY}{T['cleaning_temp']}{RESET_COLOR}")
        shutil.rmtree(temp_dir)
        
    print(f"\n{C_GREEN}{T['export_done']}{RESET_COLOR}{output_v}")

# ── Playback Engine ───────────────────────────────────────────────────────────

def play_engine(video_path, width, use_color, skip, loop):
    cap = cv2.VideoCapture(video_path)
    info = get_video_info(cap); fps = info["fps"] if info["fps"]>0 else 30.0
    delay = (1.0 / fps) * skip; video_ar = info["width_px"] / info["height_px"]
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        q = Queue(maxsize=10); stop = threading.Event()
        def _dec():
            idx = 0
            while not stop.is_set():
                ret, f = cap.read()
                if not ret: break
                if skip>1 and idx%skip!=0: idx+=1; continue
                idx+=1
                while not stop.is_set():
                    try: q.put(f, timeout=0.1); break
                    except: pass
            q.put(None)
        t = threading.Thread(target=_dec, daemon=True); t.start()
        sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN); sys.stdout.flush()
        f_cnt = 0; tot = max(1, info["total_frames"] // skip)
        try:
            while True:
                ts = time.perf_counter()
                f = q.get(timeout=2.0)
                if f is None: break
                f_cnt += 1
                try: ts_cols, ts_lines = os.get_terminal_size().columns, os.get_terminal_size().lines
                except: ts_cols, ts_lines = 80, 24
                if width is None:
                    avail_h = max(1, ts_lines - 2)
                    w_from_h = int(avail_h * video_ar * 2.0)
                    cur_w = min(ts_cols, w_from_h)
                else: cur_w = width
                
                if use_color:
                    cmap, rgb = frame_to_ascii_color(f, cur_w)
                    art = "\n".join(["".join([f"\033[38;2;{r};{g};{b}m{c}" for c, (r,g,b) in zip(row, rgb_row)]) + RESET_COLOR for row, rgb_row in zip(cmap, rgb)])
                else: art = frame_to_ascii_nocolor(f, cur_w)
                
                sys.stdout.write(CURSOR_HOME + art)
                bar_l = max(10, ts_cols - 45); filled = int(bar_l * (f_cnt/tot))
                bar = "█" * filled + "░" * (bar_l - filled)
                sys.stdout.write(f"\033[{ts_lines};1H{C_GRAY}[{bar}] {f_cnt}/{tot} | Ctrl+C {RESET_COLOR}")
                sys.stdout.flush()
                elap = time.perf_counter() - ts
                if delay - elap > 0: time.sleep(delay - elap)
        except KeyboardInterrupt: stop.set(); break
        finally: stop.set(); t.join(timeout=1.0)
        if not loop: break
    cap.release(); sys.stdout.write(SHOW_CURSOR + RESET_COLOR + f"\n\n{T['playback_finished']}\n")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    enable_ansi_windows()
    
    while True:
        show_logo()
        print(f"  {C_BOLD}{C_YELLOW}» {T['app_name']} «{RESET_COLOR}\n")
        vid = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['input_path']}").strip().strip('"')
        if not vid or not os.path.exists(vid):
            print(f"  {C_RED}{T['error_not_found'].format(vid)}{RESET_COLOR}"); time.sleep(2); continue
            
        color_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['enable_color']}").strip().lower()
        use_color = color_in in ["s", "y", "o", "j"]
        
        try: ts_cols = os.get_terminal_size().columns
        except: ts_cols = 80
        w_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['output_width'].format(ts_cols)}").strip()
        width = int(w_in) if w_in else None
        
        s_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['skip_n_frames']}").strip()
        skip = int(s_in) if s_in else 1
        
        loop_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['repeat_video']}").strip().lower()
        loop = loop_in in ["s", "y", "o", "j"]
        
        # Playback
        try: play_engine(vid, width, use_color, skip, loop)
        except KeyboardInterrupt: pass
        
        # Export
        exp_in = input(f"\n  {C_BOLD}{C_YELLOW}»{RESET_COLOR} {T['export_q']}").strip().lower()
        if exp_in in ["s", "y", "o", "j"]:
            export_flow(vid, use_color, width if width else 120)
            
        retry = input(f"\n  {C_BOLD}{C_CYAN}»{RESET_COLOR} {T['try_again_q']}").strip().lower()
        if retry not in ["s", "y", "o", "j"]: break

    clear_console()
    print("\n  Thanks for using ASCII Player Video Creator!\n Follow us on instagram! @z3usx01 & @johan_cicada")

if __name__ == "__main__":
    main()