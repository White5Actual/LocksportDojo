# Save as 'xpt2046.py'
from machine import Pin, SPI
import time

class Touch:
    #  CALIBRATION (768, 3684) -> (3472, 357)
    def __init__(self, spi, cs, int_pin=None, cal_x0=768, cal_y0=3684, cal_x1=3472, cal_y1=357):
        self.spi = spi
        self.cs = cs
        self.cs.init(self.cs.OUT, value=1)
        self.rx = bytearray(3)
        self.tx = bytearray(3)
        self.cal_x0 = cal_x0
        self.cal_y0 = cal_y0
        self.cal_x1 = cal_x1
        self.cal_y1 = cal_y1
        
    def get_touch(self):
        # NOISE FILTER: Take 3 samples. If they are consistent, return the average.
        # If they are wild (noise), return None.
        x1, y1 = self.raw_sample()
        if x1 == 0: return None # No touch
        
        # Small delay to let signal settle
        time.sleep_ms(2) 
        x2, y2 = self.raw_sample()
        
        time.sleep_ms(2)
        x3, y3 = self.raw_sample()
        
        # If any sample was empty, it was just a blip. Ignore it.
        if x2 == 0 or x3 == 0: return None
        
        # Check if samples are close to each other (within 50 raw units)
        # This proves it's a finger holding still, not a static spike.
        if abs(x1 - x2) > 50 or abs(x1 - x3) > 50 or abs(y1 - y2) > 50:
            return None
            
        # Average the 3 valid samples for high precision
        avg_x = (x1 + x2 + x3) // 3
        avg_y = (y1 + y2 + y3) // 3
        
        return self.normalize(avg_x, avg_y)

    def raw_sample(self):
        x = self.send_command(0xD0)
        y = self.send_command(0x90)
        # Ignore extreme edge values (often noise)
        if x < 100 or y < 100 or x > 4000 or y > 4000: 
            return (0, 0)
        return (x, y)

    def send_command(self, cmd):
        self.tx[0] = cmd
        self.cs(0)
        self.spi.write_readinto(self.tx, self.rx)
        self.cs(1)
        return (self.rx[1] << 8 | self.rx[2]) >> 3

    def normalize(self, x, y):
        # Map raw hardware values to screen pixels (0-240, 0-320)
        disp_x = (x - self.cal_x0) * 240 // (self.cal_x1 - self.cal_x0)
        disp_y = (y - self.cal_y0) * 320 // (self.cal_y1 - self.cal_y0)
        return (max(0, min(240, disp_x)), max(0, min(320, disp_y)))
