import machine, time, os, json, random, gc
from ili9341 import Display, color565
from xpt2046 import Touch

# --- 1. HARDWARE INIT ---
try:
    s = machine.SDCard(slot=2)
    s.deinit()
    del s
    time.sleep(0.1)
except: pass

# Backlight PWM
bl = machine.PWM(machine.Pin(21), freq=1000)
bl.duty(1023)

# Battery ADC (Pin 34)
batt_adc = machine.ADC(machine.Pin(34))
batt_adc.atten(machine.ADC.ATTN_11DB) 

spi = machine.SPI(1, baudrate=40000000, sck=machine.Pin(14), mosi=machine.Pin(13))
display = Display(spi, dc=machine.Pin(2), cs=machine.Pin(15), rst=machine.Pin(12))
touch_spi = machine.SoftSPI(baudrate=1000000, sck=machine.Pin(25), mosi=machine.Pin(32), miso=machine.Pin(39))
touch = Touch(touch_spi, cs=machine.Pin(33))

# --- 2. CONFIG & COLORS ---
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GREY = color565(50, 50, 50)
LIGHT_GREY = color565(100, 100, 100)
GREEN = color565(0, 255, 0)
RED = color565(255, 0, 0)
BLUE = color565(0, 0, 255)
GOLD = color565(255, 215, 0)
CYAN = color565(0, 255, 255)
PURPLE = color565(128, 0, 128)
ORANGE = color565(255, 165, 0)

BELT_ORDER = ["White", "Yellow", "Orange", "Green", "Blue", "Purple", "Brown", "Red", "Black"]
BELT_COLORS = {
    "White": WHITE, "Yellow": color565(255, 255, 0), "Orange": color565(255, 165, 0),
    "Green": GREEN, "Blue": BLUE, "Purple": color565(128, 0, 128),
    "Brown": color565(165, 42, 42), "Red": RED, "Black": GREY
}

# --- 3. LOGGING & ACHIEVEMENTS ---
OPT_TOOLS = ["Short Hook", "Med Hook", "Deep Hook", "Gem", "City Rake", "Bogota", "Diamond", "L-Rake"]
OPT_PICK_SIZE = ["0.025", "0.023", "0.020", "0.019", "0.018", "0.015"]
OPT_TEN_SIZE = ["0.050", "0.040", "0.032", "0.030", "0.025", "Variable"]
OPT_STYLE = ["TOK", "BOK"]
OPT_TENSION = ["Prybar", "Wiper", "Heavy", "Medium", "Light"]

# Default date (since no WiFi)
draft_log = {"y": 2026, "m": 1, "d": 1, "tool": 0, "p_size": 0, "t_size": 0, "style": 0, "tension": 0, "dur": None, "rating": 3}
timer_running = False
timer_start = 0
timer_elapsed = 0

ACHIEVEMENTS = [
    {"id": "beginner", "name": "Beginner", "desc": "1st Lock Picked"},
    {"id": "novice", "name": "Novice", "desc": "10 Locks Picked"},
    {"id": "expert", "name": "Expert", "desc": "50 Locks Picked"},
    {"id": "collector", "name": "Collector", "desc": "Own 10 Locks"},
    {"id": "hoarder", "name": "Hoarder", "desc": "Own 25 Locks"},
    {"id": "speed", "name": "Speed Demon", "desc": "Pick in < 30s"},
    {"id": "lightning", "name": "Lightning", "desc": "Pick in < 10s"},
    {"id": "tech", "name": "Technician", "desc": "20 TOK Picks"},
    {"id": "raker", "name": "Raker", "desc": "20 Rake Picks"},
    {"id": "globe", "name": "Globetrotter", "desc": "Picks in 3 Belts"}
]

# --- 4. DATA MANAGER ---
db = {"locks": {}, "user": {"owned": [], "picked": [], "logs": {}, "trophies": [], "auto_dim": True, "show_batt": True}}
current_belt = "Green"
current_page = 0
items_per_page = 8
return_screen = "HOME"

def load_data():
    global db
    try:
        sd = machine.SDCard(slot=2, width=1, cd=None, wp=None, sck=machine.Pin(18), miso=machine.Pin(19), mosi=machine.Pin(23), cs=machine.Pin(5))
        try: os.mount(sd, "/sd")
        except: pass
        
        with open("/sd/data/locks.json", "r") as f:
            db["locks"] = json.load(f)
        try:
            with open("/sd/data/user_progress.json", "r") as f:
                db["user"] = json.load(f)
                if "logs" not in db["user"]: db["user"]["logs"] = {}
                if "trophies" not in db["user"]: db["user"]["trophies"] = []
                if "auto_dim" not in db["user"]: db["user"]["auto_dim"] = True
                if "show_batt" not in db["user"]: db["user"]["show_batt"] = True
        except: save_data()
    except Exception as e: print("SD Error:", e)

def save_data():
    try:
        with open("/sd/data/user_progress.json", "w") as f:
            json.dump(db["user"], f)
    except: pass

def perform_factory_reset():
    db["user"] = {"owned": [], "picked": [], "logs": {}, "trophies": [], "auto_dim": True, "show_batt": True}
    save_data()

def check_achievements():
    changed = False
    total_logs = sum(len(v) for v in db["user"]["logs"].values())
    total_owned = len(db["user"]["owned"])
    total_picked_status = len(db["user"]["picked"])
    
    if (total_logs >= 1 or total_picked_status >= 1) and "beginner" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("beginner"); changed = True
    if (total_logs >= 10 or total_picked_status >= 10) and "novice" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("novice"); changed = True
    if (total_logs >= 50 or total_picked_status >= 50) and "expert" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("expert"); changed = True
    if total_owned >= 10 and "collector" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("collector"); changed = True
    if total_owned >= 25 and "hoarder" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("hoarder"); changed = True

    belts_picked = set()
    for belt in BELT_ORDER:
        belt_locks = [l['n'] for l in db["locks"].get(belt, [])]
        picked_in_belt = any(l in db["user"]["picked"] for l in belt_locks)
        if picked_in_belt: belts_picked.add(belt)
    if len(belts_picked) >= 3 and "globe" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("globe"); changed = True

    tok_count = 0; rake_count = 0
    for lock_logs in db["user"]["logs"].values():
        for log in lock_logs:
            if log.get('style') == "TOK": tok_count += 1
            t_name = log.get('tool', '').lower()
            if "rake" in t_name or "bogota" in t_name or "city" in t_name: rake_count += 1
    if tok_count >= 20 and "tech" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("tech"); changed = True
    if rake_count >= 20 and "raker" not in db["user"]["trophies"]:
        db["user"]["trophies"].append("raker"); changed = True

    if changed: save_data()

# --- UTILITIES ---
def get_battery_pct():
    try:
        raw = batt_adc.read()
        pct = int((raw - 1800) / (2350 - 1800) * 100)
        if pct > 100: pct = 100
        if pct < 0: pct = 0
        return pct
    except: return 0

def export_csv():
    try:
        with open("/sd/data/locks_export.csv", "w") as f:
            f.write("Lock Name,Date,Time,Tool,Pick Size,Tension,Rating\n")
            for lock_name, entries in db["user"]["logs"].items():
                for e in entries:
                    f.write("{},{},{},{},{},{},{}\n".format(
                        lock_name, e['date'], e.get('dur',''), e.get('tool',''),
                        e.get('p_size',''), e.get('tension',''), e.get('rating','')))
        return True
    except: return False

def toggle_status(lock_name, list_type):
    if lock_name in db["user"][list_type]: db["user"][list_type].remove(lock_name)
    else: db["user"][list_type].append(lock_name)
    save_data(); check_achievements()

def full_remove_lock(lock_name):
    changed = False
    if lock_name in db["user"]["owned"]: db["user"]["owned"].remove(lock_name); changed = True
    if lock_name in db["user"]["picked"]: db["user"]["picked"].remove(lock_name); changed = True
    if changed: save_data()

def add_log_entry(lock_name):
    if lock_name not in db["user"]["logs"]: db["user"]["logs"][lock_name] = []
    d_str = "{}-{:02d}-{:02d}".format(draft_log['y'], draft_log['m'], draft_log['d'])
    entry = {
        "date": d_str, "tool": OPT_TOOLS[draft_log['tool']],
        "p_size": OPT_PICK_SIZE[draft_log['p_size']], "t_size": OPT_TEN_SIZE[draft_log['t_size']],
        "style": OPT_STYLE[draft_log['style']], "tension": OPT_TENSION[draft_log['tension']],
        "dur": draft_log['dur'], "rating": draft_log['rating']
    }
    db["user"]["logs"][lock_name].insert(0, entry)
    if draft_log['dur']:
        parts = draft_log['dur'].split(':')
        sec = (int(parts[0]) * 60) + int(parts[1])
        if sec < 30 and "speed" not in db["user"]["trophies"]: db["user"]["trophies"].append("speed")
        if sec < 10 and "lightning" not in db["user"]["trophies"]: db["user"]["trophies"].append("lightning")
    save_data(); check_achievements()

def delete_log_entry(lock_name, index):
    if lock_name in db["user"]["logs"]:
        if index < len(db["user"]["logs"][lock_name]):
            del db["user"]["logs"][lock_name][index]
            save_data()

def get_owned_locks():
    collection = []
    seen = [] 
    for belt in BELT_ORDER:
        for lock in db["locks"].get(belt, []):
            if lock['n'] in db["user"]["owned"] and lock['n'] not in seen:
                lock['_belt'] = belt
                collection.append(lock); seen.append(lock['n'])
    return collection

def get_user_rank():
    for belt in reversed(BELT_ORDER):
        for lock in db["locks"].get(belt, []):
            if lock['n'] in db["user"]["picked"]: return belt
    return "White"

def calc_stats():
    total_logs = sum(len(v) for v in db["user"]["logs"].values())
    fastest = None
    tools = {}
    for lock, entries in db["user"]["logs"].items():
        for entry in entries:
            t = entry.get('tool', 'Unknown')
            tools[t] = tools.get(t, 0) + 1
            if 'dur' in entry and entry['dur']:
                if fastest is None or entry['dur'] < fastest: fastest = entry['dur']
    fav_tool = max(tools, key=tools.get) if tools else "None"
    return total_logs, fav_tool, (fastest if fastest else "--:--")

def draw_btn(x, y, w, h, text, color, text_color=WHITE):
    display.fill_rectangle(x, y, w, h, color)
    t_x = x + (w // 2) - (len(text) * 4) 
    t_y = y + (h // 2) - 4
    display.draw_text(text, t_x, t_y, text_color, color)

def draw_header(text, bg_color=GREY, text_color=WHITE):
    display.fill_rectangle(0, 0, 240, 35, bg_color)
    display.draw_text(text, 10, 10, text_color, bg_color)
    draw_btn(180, 5, 55, 25, "MENU", LIGHT_GREY, WHITE)

def draw_battery_icon():
    if not db["user"].get("show_batt", True): return
    pct = get_battery_pct()
    c = GREEN
    if pct < 20: c = RED
    elif pct < 50: c = ORANGE
    display.fill_rectangle(215, 5, 20, 1, WHITE) 
    display.fill_rectangle(215, 14, 20, 1, WHITE)
    display.fill_rectangle(215, 5, 1, 10, WHITE)
    display.fill_rectangle(234, 5, 1, 10, WHITE)
    display.fill_rectangle(235, 7, 2, 6, WHITE)
    w = int(18 * (pct / 100))
    if w > 0: display.fill_rectangle(216, 6, w, 8, c)

def adjust_val(val, delta, min_v, max_v):
    new_v = val + delta
    if new_v > max_v: return min_v
    if new_v < min_v: return max_v
    return new_v

def adjust_idx(idx, delta, length):
    return (idx + delta) % length

def format_time(ms):
    seconds = int(ms / 1000)
    return "{:02d}:{:02d}".format((seconds // 60) % 60, seconds % 60)

DIGIT_MAP = {'0':[1,1,1,1,0,1,1,0,1,1,0,1,1,1,1],'1':[0,1,0,0,1,0,0,1,0,0,1,0,0,1,0],'2':[1,1,1,0,0,1,1,1,1,1,0,0,1,1,1],'3':[1,1,1,0,0,1,0,1,1,0,0,1,1,1,1],'4':[1,0,1,1,0,1,1,1,1,0,0,1,0,0,1],'5':[1,1,1,1,0,0,1,1,1,0,0,1,1,1,1],'6':[1,1,1,1,0,0,1,1,1,1,0,1,1,1,1],'7':[1,1,1,0,0,1,0,0,1,0,0,1,0,0,1],'8':[1,1,1,1,0,1,1,1,1,1,0,1,1,1,1],'9':[1,1,1,1,0,1,1,1,1,0,0,1,1,1,1],':':[0,0,0,0,1,0,0,0,0,0,1,0,0,0,0]}
SKULL_ICON = [0,0,1,1,1,1,1,1,0,0,0,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,0,0,1,1,1,1,1,0,0,1,0,0,1,1,1,1,1,1,1,0,1,1,1,1,0,1,1,1,1,1,1,1,1,0,0,0,1,0,1,0,1,0,1,0,0,0,1,1,1,1,1,1,1,0]

def draw_big_char(x, y, char, color, bg_color, size=10):
    grid = DIGIT_MAP.get(char, DIGIT_MAP[':'])
    for r in range(5):
        for c in range(3):
            fill = color if grid[r*3 + c] else bg_color
            display.fill_rectangle(x + (c * size), y + (r * size), size, size, fill)

def draw_big_time(x, y, text, color, bg_color, size=10):
    cursor_x = x
    for char in text:
        draw_big_char(cursor_x, y, char, color, bg_color, size)
        cursor_x += (4 * size)

def draw_skull_icon(cx, cy, color, size=10):
    start_x = cx - (5 * size)
    start_y = cy - (4 * size)
    for r in range(9):
        for c in range(10):
            if SKULL_ICON[r*10 + c] == 1:
                display.fill_rectangle(start_x + (c*size), start_y + (r*size), size, size, color)

def draw_belt_graphic(cx, cy, color):
    oc = BLACK 
    def rect(x, y, w, h, c):
        display.fill_rectangle(x, y, w, h, oc) 
        display.fill_rectangle(x+2, y+2, w-4, h-4, c) 
    rect(cx - 35, cy + 10, 25, 50, color)
    rect(cx + 10, cy + 10, 25, 50, color)
    rect(cx - 60, cy - 15, 120, 30, color)
    rect(cx - 20, cy - 20, 40, 40, color)
    display.fill_rectangle(cx - 20, cy, 40, 2, oc)

# --- 7. SCREENS ---
active_screen = "SPLASH"
selected_lock = None

def screen_splash():
    display.fill_rectangle(0, 0, 240, 320, WHITE)
    draw_skull_icon(120, 140, BLACK, size=15)
    display.draw_text("W5A", 108, 220, BLACK, WHITE)
    free_ram = gc.mem_free() // 1024
    display.draw_text("RAM: {} KB".format(free_ram), 80, 250, GREY, WHITE)
    display.draw_text("touch anywhere", 65, 280, BLACK, WHITE)

def screen_home():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    display.fill_rectangle(0, 0, 240, 50, GREY)
    
    rank = get_user_rank()
    rank_color = BELT_COLORS.get(rank, WHITE)
    t_color = BLACK if rank in ["White", "Yellow", "Orange"] else WHITE
    draw_btn(0, 0, 240, 60, "Locksport Dojo", rank_color, t_color)
    draw_battery_icon()
    
    draw_btn(10, 70, 105, 60, "LIBRARY", BLUE)
    draw_btn(125, 70, 105, 60, "COLLECTION", GOLD, BLACK)
    draw_btn(10, 140, 105, 60, "TRAINING", ORANGE, BLACK)
    draw_btn(125, 140, 105, 60, "STATS", PURPLE)
    
    owned = len(db["user"]["owned"])
    picked = len(db["user"]["picked"])
    display.draw_text("Owned: {}".format(owned), 20, 220, BLUE, BLACK)
    display.draw_text("Picked: {}".format(picked), 140, 220, GREEN, BLACK)
    
    draw_btn(20, 260, 200, 40, "SETTINGS", GREY)

def screen_settings():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("SETTINGS")
    batt_status = "ON" if db["user"].get("show_batt", True) else "OFF"
    batt_color = GREEN if db["user"].get("show_batt", True) else RED
    dim_status = "ON" if db["user"].get("auto_dim", True) else "OFF"
    dim_color = GREEN if db["user"].get("auto_dim", True) else RED
    
    draw_btn(20, 50, 200, 35, "EXPORT DATA CSV", GREEN, BLACK)
    draw_btn(20, 95, 200, 35, "AUTO DIM: " + dim_status, dim_color, BLACK)
    draw_btn(20, 140, 200, 35, "BATTERY: " + batt_status, batt_color, BLACK)
    draw_btn(20, 185, 200, 35, "FILE EXPLORER", BLUE, WHITE)
    draw_btn(20, 230, 200, 35, "FACTORY RESET", RED, WHITE)
    draw_btn(0, 280, 240, 40, "BACK", GREY)

def screen_files():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("SD FILES")
    y = 50
    try:
        for f in os.listdir("/sd"):
            if f == "data": continue
            display.draw_text("/" + f, 10, y, WHITE, BLACK)
            y += 20
        for f in os.listdir("/sd/data"):
            display.draw_text("/data/" + f, 10, y, GOLD, BLACK)
            y += 20
    except: display.draw_text("Error Reading SD", 10, 50, RED, BLACK)
    draw_btn(0, 280, 240, 40, "BACK", GREY)

def screen_reset_confirm():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("CONFIRM RESET")
    display.draw_text("DELETE ALL DATA?", 30, 100, RED, BLACK)
    display.draw_text("Cannot be undone.", 35, 130, WHITE, BLACK)
    draw_btn(20, 180, 90, 50, "NO", GREEN, BLACK)
    draw_btn(130, 180, 90, 50, "YES", RED, WHITE)

def screen_trophies():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("TROPHIES")
    y = 50
    start_idx = current_page * 5
    page_trophies = db["user"]["trophies"][start_idx:start_idx+5]
    if not db["user"]["trophies"]: display.draw_text("No trophies yet!", 50, 150, GREY, BLACK)
    else:
        for t_id in page_trophies:
            data = next((item for item in ACHIEVEMENTS if item["id"] == t_id), None)
            if data:
                display.fill_rectangle(10, y, 220, 40, GREY)
                display.fill_rectangle(10, y, 40, 40, GOLD) 
                display.draw_text(data["name"], 60, y+5, GOLD, GREY)
                display.draw_text(data["desc"], 60, y+20, WHITE, GREY)
                y += 50
    draw_btn(0, 280, 70, 40, "BACK", RED)
    if start_idx > 0: draw_btn(80, 280, 70, 40, "< PREV", BLUE)
    if start_idx + 5 < len(db["user"]["trophies"]): draw_btn(160, 280, 70, 40, "NEXT >", BLUE)

def screen_stats():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("DOJO STATS")
    logs, fav, fast = calc_stats()
    display.draw_text("TOTAL LOGS:", 10, 60, WHITE, BLACK)
    display.draw_text(str(logs), 10, 80, GREEN, BLACK)
    display.draw_text("FAVORITE TOOL:", 10, 120, WHITE, BLACK)
    display.draw_text(fav[:18], 10, 140, CYAN, BLACK)
    display.draw_text("FASTEST PICK:", 10, 180, WHITE, BLACK)
    display.draw_text(fast, 10, 200, GOLD, BLACK)
    draw_btn(40, 230, 160, 40, "VIEW TROPHIES", GOLD, BLACK)
    draw_btn(0, 280, 240, 40, "BACK", RED)

def screen_roulette():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("TRAINING")
    owned = get_owned_locks()
    if not owned:
        display.draw_text("No locks owned!", 50, 150, RED, BLACK)
        draw_btn(0, 280, 240, 40, "BACK", RED)
        return
    target = random.choice(owned)
    display.draw_text("CHALLENGE LOCK:", 20, 60, WHITE, BLACK)
    display.fill_rectangle(20, 90, 200, 100, GREY)
    name = target['n']
    belt = target.get('_belt', 'White')
    b_color = BELT_COLORS.get(belt, WHITE)
    display.draw_text(name[:18], 30, 110, WHITE, GREY)
    if len(name) > 18: display.draw_text(name[18:36], 30, 130, WHITE, GREY)
    display.draw_text(belt.upper() + " BELT", 30, 160, b_color, GREY)
    draw_btn(20, 210, 200, 50, "SPIN AGAIN", ORANGE, BLACK)
    draw_btn(0, 280, 240, 40, "BACK", RED)

def screen_my_belt():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("CURRENT RANK")
    rank = get_user_rank()
    rank_color = BELT_COLORS.get(rank, WHITE)
    txt = rank.upper() + " BELT"
    t_x = 120 - (len(txt) * 4) 
    display.draw_text(txt, t_x, 70, rank_color, BLACK)
    draw_belt_graphic(120, 170, rank_color)
    draw_btn(0, 280, 240, 40, "BACK TO HOME", GREY)

def screen_belts():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("SELECT BELT")
    y = 40
    for i, belt in enumerate(BELT_ORDER):
        color = BELT_COLORS.get(belt, WHITE)
        t_color = BLACK if belt in ["White", "Yellow", "Orange"] else WHITE
        x = 10 if i % 2 == 0 else 125
        draw_btn(x, y, 105, 40, belt.upper(), color, t_color)
        if i % 2 == 1: y += 50

def screen_list(belt):
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    b_color = BELT_COLORS.get(belt, WHITE)
    t_color = BLACK if belt in ["White", "Yellow", "Orange"] else WHITE
    draw_header("{} LOCKS".format(belt.upper()), b_color, t_color)
    all_locks = db["locks"].get(belt, [])
    start = current_page * items_per_page
    page_locks = all_locks[start:start + items_per_page]
    draw_lock_list(page_locks, start, len(all_locks))

def screen_collection():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("MY COLLECTION", GOLD, BLACK)
    all_locks = get_owned_locks()
    start = current_page * items_per_page
    page_locks = all_locks[start:start + items_per_page]
    draw_lock_list(page_locks, start, len(all_locks))

def draw_lock_list(locks, start_idx, total_count):
    y = 45
    for lock in locks:
        full_name = lock['n']
        trunc = 18 if active_screen == "COLLECTION" else 22
        disp_name = full_name[:trunc]
        c = WHITE
        prefix = " "
        if full_name in db["user"]["picked"]: c, prefix = GREEN, "P"
        elif active_screen == "LIST" and full_name in db["user"]["owned"]: c, prefix = GOLD, "*"
        if active_screen == "COLLECTION":
            display.fill_rectangle(5, y, 200, 25, GREY)
            display.fill_rectangle(210, y, 25, 25, RED)
            display.draw_text("X", 218, y+8, WHITE, RED)
        else:
            display.fill_rectangle(5, y, 230, 25, GREY)
        display.draw_text("{} {}".format(prefix, disp_name), 10, y+8, c, GREY)
        y += 28
    draw_btn(0, 280, 70, 40, "BACK", GREY)
    if start_idx > 0: draw_btn(80, 280, 70, 40, "< PREV", BLUE)
    if start_idx + len(locks) < total_count: draw_btn(160, 280, 70, 40, "NEXT >", BLUE)

def screen_detail(lock):
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header(lock['n'][:18], GREY)
    is_owned = lock['n'] in db["user"]["owned"]
    is_picked = lock['n'] in db["user"]["picked"]
    draw_btn(10, 40, 105, 40, "OWNED" if is_owned else "NOT OWNED", GREEN if is_owned else GREY)
    draw_btn(125, 40, 105, 40, "PICKED" if is_picked else "NOT PICKED", GOLD if is_picked else GREY, BLACK if is_picked else WHITE)
    display.fill_rectangle(0, 95, 240, 2, BLUE)
    display.draw_text("LOGBOOK", 10, 105, BLUE, BLACK)
    logs = db["user"]["logs"].get(lock['n'], [])
    y = 125
    if not logs: display.draw_text("No logs yet.", 10, y, LIGHT_GREY, BLACK)
    else:
        for i, log in enumerate(logs[:3]):
            tool_name = log.get('tool', 'Unknown')
            date_short = log['date'][5:]
            time_str = ""
            if 'dur' in log and log['dur']: time_str = "({})".format(log['dur'])
            rating = log.get('rating', 0)
            star_str = "*" * rating
            txt = "{}{} {}".format(date_short, time_str, star_str)
            display.draw_text(txt, 10, y, WHITE, BLACK)
            y += 20
    draw_btn(20, 200, 100, 40, "MANUAL LOG", BLUE)
    draw_btn(130, 200, 90, 40, "TIMER", CYAN, BLACK)
    draw_btn(20, 250, 200, 40, "VIEW HISTORY", LIGHT_GREY)
    draw_btn(0, 300, 80, 20, "< BACK", RED)

def screen_timer():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("STOPWATCH")
    display.fill_rectangle(20, 60, 200, 60, GREY)
    draw_big_time(25, 65, "00:00", WHITE, GREY, size=10)
    if not timer_running:
        draw_btn(20, 160, 100, 50, "START", GREEN)
    else:
        draw_btn(20, 160, 100, 50, "STOP", RED)
    draw_btn(130, 160, 90, 50, "RESET", LIGHT_GREY, BLACK)
    draw_btn(40, 220, 160, 50, "LOG THIS PICK", BLUE)
    draw_btn(0, 290, 80, 30, "CANCEL", RED)

def screen_add_log():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("NEW LOG ENTRY")
    y_off = 20 if draft_log['dur'] else 0
    if draft_log['dur']: display.draw_text("TIME: " + draft_log['dur'], 80, 40, CYAN, BLACK)
    def draw_split_btn(x, y, w, text):
        draw_btn(x, y, w, 30, text, GREY)
        display.fill_rectangle(x + (w // 2), y+2, 1, 26, BLACK)
    y = 40 + y_off
    
    # Manual Date Controls (Since we lost WiFi sync)
    draw_split_btn(5, y, 70, "< {:02d} >".format(draft_log['m']))
    draw_split_btn(85, y, 70, "< {:02d} >".format(draft_log['d']))
    draw_split_btn(165, y, 70, "< {} >".format(str(draft_log['y'])[-2:]))
    y += 35
    
    display.draw_text("Tool:", 5, y+5, WHITE, BLACK)
    draw_btn(50, y, 180, 30, "< {} >".format(OPT_TOOLS[draft_log['tool']]), BLUE)
    y += 35
    display.draw_text("Size:", 5, y+5, WHITE, BLACK)
    draw_btn(50, y, 180, 30, "< P:{} / T:{} >".format(OPT_PICK_SIZE[draft_log['p_size']], OPT_TEN_SIZE[draft_log['t_size']]), BLUE)
    y += 35
    draw_btn(5, y, 110, 30, "< {} >".format(OPT_STYLE[draft_log['style']]), BLUE)
    draw_btn(125, y, 110, 30, "< {} >".format(OPT_TENSION[draft_log['tension']]), BLUE)
    y += 35
    display.draw_text("Diff:", 5, y+5, WHITE, BLACK)
    draw_btn(50, y, 180, 30, "< {} STARS >".format(draft_log['rating']), GOLD, BLACK)
    draw_btn(10, 270, 105, 40, "CANCEL", RED)
    draw_btn(125, 270, 105, 40, "SAVE LOG", GREEN)

def screen_history():
    display.fill_rectangle(0, 0, 240, 320, BLACK)
    draw_header("PICK HISTORY")
    logs = db["user"]["logs"].get(selected_lock['n'], [])
    if not logs: display.draw_text("No records found.", 50, 150, WHITE, BLACK)
    y = 40
    for log in logs[:4]:
        p_sz = log.get('p_size', '?')
        t_sz = log.get('t_size', '?')
        display.fill_rectangle(5, y, 200, 55, GREY)
        display.fill_rectangle(210, y, 25, 55, RED)
        display.draw_text("X", 218, y+20, WHITE, RED)
        time_str = ""
        if 'dur' in log and log['dur']: time_str = "({})".format(log['dur'])
        rating = log.get('rating', 0)
        stars = "*" * rating
        line1 = "{} {} {}".format(log['date'], time_str, stars)
        line2 = "{} ({})".format(log['tool'], p_sz)
        line3 = "Ten: {} ({})".format(log['tension'], t_sz)
        display.draw_text(line1, 10, y+5, GOLD, GREY)
        display.draw_text(line2, 10, y+20, WHITE, GREY)
        display.draw_text(line3, 10, y+35, WHITE, GREY)
        y += 60
    draw_btn(0, 280, 240, 40, "< BACK", RED)

# --- MAIN LOOP ---
load_data()
screen_splash()
last_touch = time.ticks_ms()
brightness_state = 2 

while True:
    # --- POWER MANAGEMENT ---
    if db["user"].get("auto_dim", True):
        idle_time = time.ticks_diff(time.ticks_ms(), last_touch)
        if idle_time < 15000: # 0-15s: High
            if brightness_state != 2: bl.duty(1023); brightness_state = 2
        elif idle_time < 30000: # 15-30s: Dim
            if brightness_state != 1: bl.duty(512); brightness_state = 1
        else: # >30s: Low
            if brightness_state != 0: bl.duty(100); brightness_state = 0
    else:
        if brightness_state != 2: bl.duty(1023); brightness_state = 2

    if active_screen == "TIMER" and timer_running:
        now = time.ticks_ms()
        diff = time.ticks_diff(now, timer_start)
        if diff // 1000 != timer_elapsed // 1000:
            timer_elapsed = diff
            draw_big_time(25, 65, format_time(timer_elapsed), WHITE, GREY, size=10)

    t = touch.get_touch()
    if t and (time.ticks_ms() - last_touch > 300):
        # WAKE UP EVENT
        x, y = t
        last_touch = time.ticks_ms() # Reset Idle Timer
        
        # If we were dim or off, just wake up and ignore the touch coordinate
        if brightness_state < 2:
            bl.duty(1023)
            brightness_state = 2
            continue 
        
        # Normal Touch Processing
        if active_screen == "SPLASH":
            active_screen = "HOME"
            screen_home()
            continue

        if active_screen != "HOME" and x > 170 and y < 40:
             timer_running = False
             active_screen = "HOME"
             screen_home()
             continue 

        if active_screen == "HOME":
            if 70 < y < 130:
                if x < 120: 
                    active_screen, return_screen = "BELTS", "BELTS"
                    screen_belts()
                else:
                    active_screen, return_screen = "COLLECTION", "COLLECTION"
                    current_page = 0
                    screen_collection()
            elif 140 < y < 200:
                if x < 120:
                    active_screen = "ROULETTE"
                    screen_roulette()
                else:
                    active_screen = "STATS"
                    screen_stats()
            elif 210 < y < 250: 
                active_screen = "MY_BELT"
                screen_my_belt()
            elif y > 260: 
                active_screen = "SETTINGS"
                screen_settings()

        elif active_screen == "SETTINGS":
            if y > 280: active_screen = "HOME"; screen_home()
            elif 50 < y < 85: # CSV
                success = export_csv()
                msg = "SAVED TO SD!" if success else "SD ERROR!"
                display.fill_rectangle(20, 100, 200, 100, BLACK)
                display.draw_text(msg, 60, 140, WHITE, BLACK)
                time.sleep(2)
                screen_settings()
            elif 95 < y < 130: # AUTO DIM
                db["user"]["auto_dim"] = not db["user"].get("auto_dim", True)
                save_data()
                screen_settings()
            elif 140 < y < 175: # BATTERY
                db["user"]["show_batt"] = not db["user"].get("show_batt", True)
                save_data()
                screen_settings()
            elif 185 < y < 220: # FILES
                active_screen = "FILES"
                screen_files()
            elif 230 < y < 265: # RESET
                active_screen = "RESET_CONFIRM"
                screen_reset_confirm()

        elif active_screen == "FILES":
            if y > 280: active_screen = "SETTINGS"; screen_settings()

        elif active_screen == "RESET_CONFIRM":
            if 180 < y < 230:
                if x < 110: 
                    active_screen = "SETTINGS"
                    screen_settings()
                elif x > 130: 
                    perform_factory_reset()
                    active_screen = "HOME"
                    screen_home()

        elif active_screen == "STATS":
            if y > 280: active_screen = "HOME"; screen_home()
            elif 230 < y < 270: 
                active_screen = "TROPHIES"
                current_page = 0
                screen_trophies()

        elif active_screen == "TROPHIES":
            if y > 280: 
                if x < 70:
                    active_screen = "STATS"
                    screen_stats()
                elif 80 < x < 150 and current_page > 0:
                    current_page -= 1
                    screen_trophies()
                elif x > 160 and (current_page + 1) * 5 < len(db["user"]["trophies"]):
                    current_page += 1
                    screen_trophies()

        elif active_screen == "MY_BELT":
            if y > 280: active_screen = "HOME"; screen_home()
        elif active_screen == "ROULETTE":
            if y > 280: active_screen = "HOME"; screen_home()
            elif 210 < y < 260: screen_roulette() 

        elif active_screen == "BELTS":
            if y > 40:
                row, col = (y - 40) // 50, 0 if x < 120 else 1
                idx = row * 2 + col
                if idx < len(BELT_ORDER):
                    current_belt, current_page, active_screen = BELT_ORDER[idx], 0, "LIST"
                    screen_list(current_belt)
        elif active_screen in ["LIST", "COLLECTION"]:
            target_locks = db["locks"].get(current_belt, []) if active_screen == "LIST" else get_owned_locks()
            if active_screen == "COLLECTION" and x > 200 and 45 < y < 270:
                 idx = (y - 45) // 28
                 real_idx = (current_page * items_per_page) + idx
                 if real_idx < len(target_locks):
                     full_remove_lock(target_locks[real_idx]['n'])
                     screen_collection()
                     continue 
            if y > 280: 
                if x < 70: 
                    active_screen = "BELTS" if active_screen == "LIST" else "HOME"
                    if active_screen == "BELTS": screen_belts()
                    else: screen_home()
                elif 80 < x < 150 and current_page > 0:
                    current_page -= 1
                    if active_screen == "LIST": screen_list(current_belt)
                    else: screen_collection()
                elif x > 160 and (current_page + 1) * items_per_page < len(target_locks):
                    current_page += 1
                    if active_screen == "LIST": screen_list(current_belt)
                    else: screen_collection()
            elif y > 45:
                idx = (y - 45) // 28
                real_idx = (current_page * items_per_page) + idx
                if real_idx < len(target_locks):
                    selected_lock = target_locks[real_idx]
                    active_screen = "DETAIL"
                    screen_detail(selected_lock)
        
        elif active_screen == "DETAIL":
            if y > 300: 
                active_screen = return_screen
                if active_screen == "COLLECTION": screen_collection()
                else: active_screen = "LIST"; screen_list(current_belt)
            elif 40 < y < 80:
                if x < 120: toggle_status(selected_lock['n'], "owned")
                else: toggle_status(selected_lock['n'], "picked")
                screen_detail(selected_lock)
            elif 200 < y < 240:
                if x < 120: 
                    draft_log['dur'] = None
                    active_screen = "ADD_LOG"
                    screen_add_log()
                else: 
                    active_screen = "TIMER"
                    timer_running = False
                    timer_elapsed = 0
                    screen_timer()
            elif 250 < y < 290: active_screen = "HISTORY"; screen_history()
            
        elif active_screen == "TIMER":
            if 160 < y < 210 and x < 125:
                if not timer_running:
                    timer_running = True
                    timer_start = time.ticks_ms() - timer_elapsed
                    draw_btn(20, 160, 100, 50, "STOP", RED)
                else:
                    timer_running = False
                    timer_elapsed = time.ticks_diff(time.ticks_ms(), timer_start)
                    draw_btn(20, 160, 100, 50, "START", GREEN)
            elif 160 < y < 210 and x > 125:
                timer_running = False
                timer_elapsed = 0
                draw_big_time(25, 65, "00:00", WHITE, GREY, size=10)
                draw_btn(20, 160, 100, 50, "START", GREEN)
            elif 220 < y < 270:
                timer_running = False
                draft_log['dur'] = format_time(timer_elapsed)
                active_screen = "ADD_LOG"
                screen_add_log()
            elif y > 290:
                timer_running = False
                active_screen = "DETAIL"
                screen_detail(selected_lock)
        
        elif active_screen == "ADD_LOG":
            y_off = 20 if draft_log['dur'] else 0
            if 30 + y_off < y < 75 + y_off: 
                if x < 80: 
                    delta = -1 if x < 40 else 1 
                    draft_log['m'] = adjust_val(draft_log['m'], delta, 1, 12)
                elif x < 160: 
                    delta = -1 if x < 120 else 1
                    draft_log['d'] = adjust_val(draft_log['d'], delta, 1, 31)
                else: 
                    delta = -1 if x < 200 else 1
                    draft_log['y'] = adjust_val(draft_log['y'], delta, 2020, 2040)
                screen_add_log()
            elif 75 + y_off < y < 110 + y_off:
                delta = -1 if x < 120 else 1
                draft_log['tool'] = adjust_idx(draft_log['tool'], delta, len(OPT_TOOLS))
                screen_add_log()
            elif 110 + y_off < y < 145 + y_off:
                if x < 120:
                    delta = -1 if x < 60 else 1
                    draft_log['p_size'] = adjust_idx(draft_log['p_size'], delta, len(OPT_PICK_SIZE))
                else:
                    delta = -1 if x < 180 else 1
                    draft_log['t_size'] = adjust_idx(draft_log['t_size'], delta, len(OPT_TEN_SIZE))
                screen_add_log()
            elif 145 + y_off < y < 180 + y_off:
                if x < 120:
                    delta = -1 if x < 60 else 1
                    draft_log['style'] = adjust_idx(draft_log['style'], delta, len(OPT_STYLE))
                else:
                    delta = -1 if x < 180 else 1
                    draft_log['tension'] = adjust_idx(draft_log['tension'], delta, len(OPT_TENSION))
                screen_add_log()
            elif 180 + y_off < y < 215 + y_off:
                delta = -1 if x < 120 else 1
                draft_log['rating'] = adjust_val(draft_log['rating'], delta, 1, 5)
                screen_add_log()
            elif y > 260:
                if x > 120: add_log_entry(selected_lock['n'])
                active_screen = "DETAIL"
                screen_detail(selected_lock)

        elif active_screen == "HISTORY":
            if y > 280: 
                active_screen = "DETAIL"
                screen_detail(selected_lock)
            elif x > 200 and y > 40:
                row_idx = (y - 40) // 60
                delete_log_entry(selected_lock['n'], row_idx)
                screen_history()

    time.sleep(0.01)
