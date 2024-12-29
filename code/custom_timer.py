from pyray import *

class Timer:
    def __init__(self, duration, autostart=True, loop=False, callback=None):
        self.duration = duration
        self.time = 0
        self.active = autostart
        self.loop = loop
        self.callback = callback
        
    def update(self):
        if not self.active:
            return
            
        self.time += get_frame_time()
        
        if self.time >= self.duration:
            if self.callback:
                self.callback()
                
            if self.loop:
                self.time = 0  # Reset for next loop
            else:
                self.active = False
                
    def activate(self):
        self.time = 0
        self.active = True
        
    def deactivate(self):
        self.active = False
        
    def is_active(self):
        return self.active
