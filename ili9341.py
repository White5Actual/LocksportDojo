# Save as 'ili9341.py'
import time
import ustruct
import font

def color565(r, g, b):
    return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3

class Display:
    def __init__(self, spi, dc, cs, rst=None, width=240, height=320, rotation=0):
        self.spi = spi
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.width = width
        self.height = height
        if self.rst:
            self.rst.init(self.rst.OUT, value=0)
            self.cs.init(self.cs.OUT, value=1)
            self.dc.init(self.dc.OUT, value=0)
            self.reset()
        self.init()

    def init(self):
        for cmd, data in (
            (0xEF, b'\x03\x80\x02'), (0xCF, b'\x00\xC1\x30'), (0xED, b'\x64\x03\x12\x81'),
            (0xE8, b'\x85\x00\x78'), (0xCB, b'\x39\x2C\x00\x34\x02'), (0xF7, b'\x20'),
            (0xEA, b'\x00\x00'), (0xC0, b'\x23'), (0xC1, b'\x10'), (0xC5, b'\x3e\x28'),
            (0xC7, b'\x86'), (0x36, b'\x88'), # \x88 = Rotated
            (0x3A, b'\x55'), (0xB1, b'\x00\x18'),
            (0xB6, b'\x08\x82\x27'), (0xF2, b'\x00'), (0x26, b'\x01'),
            (0xE0, b'\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00'),
            (0xE1, b'\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F')):
            self._write(cmd, data)
        self._write(0x11)
        time.sleep_ms(120)
        self._write(0x29)

    def _write(self, cmd, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytearray([cmd]))
        if data:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def reset(self):
        self.rst(0)
        time.sleep_ms(50)
        self.rst(1)
        time.sleep_ms(50)

    def _set_window(self, x0, y0, x1, y1):
        self._write(0x2A, ustruct.pack(">HH", x0, x1))
        self._write(0x2B, ustruct.pack(">HH", y0, y1))
        self._write(0x2C)

    def fill_rectangle(self, x, y, w, h, color):
        x = min(self.width - 1, max(0, x))
        y = min(self.height - 1, max(0, y))
        w = min(self.width - x, max(1, w))
        h = min(self.height - y, max(1, h))
        if w == 0 or h == 0: return
        self._set_window(x, y, x + w - 1, y + h - 1)
        
        # Fast Block Write
        chunk_size = 1024
        line_buffer = ustruct.pack(">H", color) * chunk_size
        pixels_total = w * h
        
        self.cs(0)
        self.dc(1)
        while pixels_total > 0:
            write_len = min(pixels_total, chunk_size)
            self.spi.write(line_buffer[:write_len * 2])
            pixels_total -= write_len
        self.cs(1)

    # --- THE SPEED UPGRADE ---
    def draw_char(self, char, x, y, color, bg_color):
        # 1. Set the 8x8 window for the character
        self._set_window(x, y, x + 7, y + 7)
        
        # 2. Get the font data
        bitmap = font.get_char(char)
        
        # 3. Pre-calculate the color bytes
        c_high, c_low = (color >> 8) & 0xFF, color & 0xFF
        bg_high, bg_low = (bg_color >> 8) & 0xFF, bg_color & 0xFF
        
        # 4. Build a buffer for the WHOLE character at once (128 bytes)
        buf = bytearray(128) 
        idx = 0
        
        for row in range(8):
            row_data = bitmap[row]
            for col in range(8):
                if row_data & (1 << (7 - col)): # If pixel is ON
                    buf[idx] = c_high
                    buf[idx+1] = c_low
                else: # If pixel is OFF
                    buf[idx] = bg_high
                    buf[idx+1] = bg_low
                idx += 2
        
        # 5. Send it all in one shot
        self.cs(0)
        self.dc(1)
        self.spi.write(buf)
        self.cs(1)

    def draw_text(self, text, x, y, color, bg_color=None):
        if bg_color is None: bg_color = 0x0000 # Default to black background if None
        for i, char in enumerate(text):
            self.draw_char(char, x + (i * 8), y, color, bg_color)
