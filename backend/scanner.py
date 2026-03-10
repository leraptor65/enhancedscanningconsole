import asyncio
import evdev
from evdev import ecodes
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Basic evdev mapping. Covers numbers, letters, space, and a few symbols.
# Shift state modifies these mappings.
KEYMAP = {
    ecodes.KEY_0: '0', ecodes.KEY_1: '1', ecodes.KEY_2: '2', ecodes.KEY_3: '3',
    ecodes.KEY_4: '4', ecodes.KEY_5: '5', ecodes.KEY_6: '6', ecodes.KEY_7: '7',
    ecodes.KEY_8: '8', ecodes.KEY_9: '9',
    ecodes.KEY_A: 'a', ecodes.KEY_B: 'b', ecodes.KEY_C: 'c', ecodes.KEY_D: 'd', 
    ecodes.KEY_E: 'e', ecodes.KEY_F: 'f', ecodes.KEY_G: 'g', ecodes.KEY_H: 'h', 
    ecodes.KEY_I: 'i', ecodes.KEY_J: 'j', ecodes.KEY_K: 'k', ecodes.KEY_L: 'l', 
    ecodes.KEY_M: 'm', ecodes.KEY_N: 'n', ecodes.KEY_O: 'o', ecodes.KEY_P: 'p', 
    ecodes.KEY_Q: 'q', ecodes.KEY_R: 'r', ecodes.KEY_S: 's', ecodes.KEY_T: 't', 
    ecodes.KEY_U: 'u', ecodes.KEY_V: 'v', ecodes.KEY_W: 'w', ecodes.KEY_X: 'x', 
    ecodes.KEY_Y: 'y', ecodes.KEY_Z: 'z',
    ecodes.KEY_MINUS: '-', ecodes.KEY_EQUAL: '=',
    ecodes.KEY_SPACE: ' ',
    ecodes.KEY_SLASH: '/', ecodes.KEY_DOT: '.', ecodes.KEY_COMMA: ','
}

SHIFT_KEYMAP = {
    ecodes.KEY_0: ')', ecodes.KEY_1: '!', ecodes.KEY_2: '@', ecodes.KEY_3: '#',
    ecodes.KEY_4: '$', ecodes.KEY_5: '%', ecodes.KEY_6: '^', ecodes.KEY_7: '&',
    ecodes.KEY_8: '*', ecodes.KEY_9: '(',
    ecodes.KEY_MINUS: '_', ecodes.KEY_EQUAL: '+',
    ecodes.KEY_SLASH: '?', ecodes.KEY_DOT: '>', ecodes.KEY_COMMA: '<'
}

class ScannerListener:
    def __init__(self, callback, device_name_substr="Zebra"):
        self.callback = callback
        self.device_name_substr = device_name_substr.lower()
        self.device = None
        self.running = False

    def find_device(self):
        try:
            paths = evdev.list_devices()
        except OSError:
            return None
        
        devices = [evdev.InputDevice(path) for path in paths]
        
        # Override with env var for dev testing if provided
        forced_dev = os.getenv("SCANNER_DEV")
        if forced_dev:
            try:
                return evdev.InputDevice(forced_dev)
            except Exception:
                logger.error(f"Could not open device {forced_dev}")
        
        for dev in devices:
            if self.device_name_substr in dev.name.lower() or "scanner" in dev.name.lower() or "barcode" in dev.name.lower():
                return dev
        return None

    async def run(self):
        self.running = True
        
        while self.running:
            try:
                if not self.device:
                    self.device = self.find_device()
                    if not self.device:
                        logger.debug(f"Scanner device containing '{self.device_name_substr}' not found. Retrying in 5s...")
                        await asyncio.sleep(5)
                        continue
                        
                    logger.info(f"Connected to scanner: {self.device.name} at {self.device.path}")
                    try:
                        self.device.grab()
                    except IOError as e:
                        logger.warning(f"Could not grab device for exclusive access (needs root?): {e}")

                barcode = ""
                shift_pressed = False
                
                async for event in self.device.async_read_loop():
                    if event.type == ecodes.EV_KEY:
                        key_event = evdev.categorize(event)
                        
                        if key_event.keystate == key_event.key_down:
                            # evdev keys map
                            scancode = event.code
                            if scancode in [ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT]:
                                shift_pressed = True
                            elif scancode == ecodes.KEY_ENTER:
                                if barcode:
                                    logger.info(f"Scanned: {barcode}")
                                    try:
                                        await self.callback(barcode)
                                    except Exception as e:
                                        logger.error(f"Callback error: {e}")
                                    barcode = ""
                            else:
                                char = ""
                                if scancode in KEYMAP:
                                    if shift_pressed:
                                        if scancode in SHIFT_KEYMAP:
                                            char = SHIFT_KEYMAP[scancode]
                                        else:
                                            char = KEYMAP[scancode].upper()
                                    else:
                                        char = KEYMAP[scancode]
                                        
                                if char:
                                    barcode += char
                                    
                        elif key_event.keystate == key_event.key_up:
                            scancode = event.code
                            if scancode in [ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT]:
                                shift_pressed = False

            except (OSError, evdev.device.EvdevError) as e:
                logger.warning(f"Scanner disconnected or error: {e}")
                self.device = None
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Unexpected Scanner task error: {e}")
                await asyncio.sleep(2)
