"""
Procedural Sound Manager — barcha ovozlar numpy + pygame.sndarray orqali generatsiya qilinadi.
Tashqi audio fayllar kerak emas.
"""

import numpy as np
import pygame
from utils.constants import (
    AUDIO_SAMPLE_RATE, AUDIO_MASTER_VOLUME,
    AUDIO_SFX_VOLUME, AUDIO_MUSIC_VOLUME, AUDIO_FOOTSTEP_INTERVAL
)

SR = AUDIO_SAMPLE_RATE


def _time_array(duration):
    """Vaqt massivi yaratish"""
    return np.linspace(0, duration, int(SR * duration), endpoint=False, dtype=np.float32)


def _make_sound(samples_float):
    """float32 mono array -> pygame.Sound (stereo, 16-bit)"""
    samples_float = np.clip(samples_float, -1.0, 1.0)
    mono_16 = (samples_float * 32767 * AUDIO_MASTER_VOLUME).astype(np.int16)
    stereo = np.column_stack((mono_16, mono_16))
    return pygame.sndarray.make_sound(stereo)


def _envelope(t, attack=0.01, decay=0.0, sustain_level=1.0, release=0.0):
    """ADSR envelope"""
    dur = t[-1] if len(t) > 0 else 0
    env = np.ones_like(t)
    if attack > 0:
        mask = t < attack
        env[mask] = t[mask] / attack
    if release > 0:
        rel_start = dur - release
        mask = t > rel_start
        env[mask] = (dur - t[mask]) / release
    if decay > 0 and sustain_level < 1.0:
        mask = (t >= attack) & (t < attack + decay)
        env[mask] = 1.0 - (1.0 - sustain_level) * ((t[mask] - attack) / decay)
        mask = t >= attack + decay
        env[mask] *= sustain_level
    return env


def _gen_shoot():
    """Qurol otish — noise burst + 50Hz bass + exp decay"""
    t = _time_array(0.15)
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32)
    bass = np.sin(2 * np.pi * 50 * t)
    decay = np.exp(-t * 30)
    return _make_sound((noise * 0.6 + bass * 0.4) * decay * 0.8)


def _gen_reload():
    """Reload — pastga freq sweep + metallik ding"""
    t = _time_array(0.4)
    # Sweep
    freq = 800 - 600 * (t / 0.4)
    sweep = np.sin(2 * np.pi * freq * t) * np.exp(-t * 5)
    # Metallik ding oxirida
    ding_start = int(0.25 * SR)
    ding = np.zeros_like(t)
    ding[ding_start:] = np.sin(2 * np.pi * 3200 * t[ding_start:]) * np.exp(-(t[ding_start:] - 0.25) * 15)
    return _make_sound((sweep * 0.5 + ding * 0.5) * 0.7)


def _gen_empty_click():
    """Bo'sh magazin — square wave click"""
    t = _time_array(0.05)
    sq = np.sign(np.sin(2 * np.pi * 800 * t))
    env = np.exp(-t * 60)
    return _make_sound(sq * env * 0.5)


def _gen_enemy_death():
    """Dushman o'limi — pastga sweep + noise"""
    t = _time_array(0.3)
    freq = 600 - 520 * (t / 0.3)
    sweep = np.sin(2 * np.pi * freq * t)
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32) * 0.3
    env = np.exp(-t * 8)
    return _make_sound((sweep * 0.7 + noise) * env * 0.7)


def _gen_hit_marker():
    """Hit marker — yuqori ding"""
    t = _time_array(0.08)
    sig = np.sin(2 * np.pi * 2500 * t) * np.exp(-t * 40)
    return _make_sound(sig * 0.6)


def _gen_player_damage():
    """O'yinchi zarar — low thump + noise"""
    t = _time_array(0.25)
    thump = np.sin(2 * np.pi * 80 * t) * np.exp(-t * 12)
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32) * np.exp(-t * 8)
    return _make_sound((thump * 0.6 + noise * 0.4) * 0.8)


def _gen_boss_start():
    """Boss jang boshlanishi — pastdan yuqoriga sweep + minor chord"""
    t = _time_array(1.0)
    freq = 80 + 400 * (t / 1.0)
    sweep = np.sin(2 * np.pi * freq * t) * 0.4
    # Minor chord: A-C-E (220, 261.6, 329.6)
    chord = (np.sin(2 * np.pi * 220 * t) +
             np.sin(2 * np.pi * 261.6 * t) +
             np.sin(2 * np.pi * 329.6 * t)) / 3
    env = _envelope(t, attack=0.1, release=0.3)
    return _make_sound((sweep + chord * 0.6) * env * 0.6)


def _gen_boss_defeated():
    """Boss yengildi — major triad fanfara (C-E-G)"""
    t = _time_array(1.5)
    # Uch nota ketma-ket
    sig = np.zeros_like(t)
    notes = [(261.6, 0.0, 0.5), (329.6, 0.4, 0.9), (392.0, 0.8, 1.5)]
    for freq, start, end in notes:
        mask = (t >= start) & (t < end)
        local_t = t[mask] - start
        note = np.sin(2 * np.pi * freq * local_t)
        note_env = np.exp(-local_t * 2)
        sig[mask] += note * note_env
    # Yakuniy akkord
    mask = t >= 1.0
    local_t = t[mask] - 1.0
    chord = (np.sin(2 * np.pi * 261.6 * local_t) +
             np.sin(2 * np.pi * 329.6 * local_t) +
             np.sin(2 * np.pi * 392.0 * local_t)) / 3
    sig[mask] += chord * np.exp(-local_t * 3)
    env = _envelope(t, attack=0.05, release=0.3)
    return _make_sound(sig * env * 0.5)


def _gen_level_complete():
    """Level tugadi — 4 nota yuqoriga (A-C#-E-A)"""
    t = _time_array(1.0)
    sig = np.zeros_like(t)
    notes = [(440, 0.0, 0.25), (554.4, 0.2, 0.45), (659.3, 0.4, 0.65), (880, 0.6, 1.0)]
    for freq, start, end in notes:
        mask = (t >= start) & (t < end)
        local_t = t[mask] - start
        note = np.sin(2 * np.pi * freq * local_t)
        note_env = np.exp(-local_t * 4)
        sig[mask] += note * note_env
    env = _envelope(t, attack=0.01, release=0.2)
    return _make_sound(sig * env * 0.6)


def _gen_game_over():
    """Game over — pastga minor chord sweep"""
    t = _time_array(1.2)
    # Pastga sweep
    freq_base = 400 - 300 * (t / 1.2)
    sig = (np.sin(2 * np.pi * freq_base * t) +
           np.sin(2 * np.pi * freq_base * 1.2 * t) +  # minor third
           np.sin(2 * np.pi * freq_base * 1.5 * t)) / 3  # fifth
    env = _envelope(t, attack=0.05, release=0.4)
    return _make_sound(sig * env * 0.6)


def _gen_powerup():
    """Powerup olish — yuqoriga sweep + sparkle"""
    t = _time_array(0.3)
    freq = 600 + 1200 * (t / 0.3)
    sweep = np.sin(2 * np.pi * freq * t) * 0.5
    sparkle = np.sin(2 * np.pi * 4000 * t) * np.exp(-t * 15) * 0.3
    env = _envelope(t, attack=0.01, release=0.1)
    return _make_sound((sweep + sparkle) * env * 0.6)


def _gen_trap():
    """Tuzoq — past square wave buzz + noise"""
    t = _time_array(0.25)
    sq = np.sign(np.sin(2 * np.pi * 150 * t))
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32) * 0.4
    env = np.exp(-t * 8)
    return _make_sound((sq * 0.5 + noise) * env * 0.7)


def _gen_key_pickup():
    """Kalit olish — ikki ding (1800+2400Hz)"""
    t = _time_array(0.2)
    ding1 = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 20)
    ding2_start = int(0.08 * SR)
    ding2 = np.zeros_like(t)
    ding2[ding2_start:] = np.sin(2 * np.pi * 2400 * t[ding2_start:]) * np.exp(-(t[ding2_start:] - 0.08) * 20)
    return _make_sound((ding1 + ding2) * 0.5)


def _gen_door_open():
    """Eshik ochilishi — past rumble + creak sweep"""
    t = _time_array(0.5)
    rumble = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 4) * 0.5
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32)
    # Creak — yuqoriga chiquvchi filtrlangan noise
    creak_freq = 200 + 800 * (t / 0.5)
    creak = np.sin(2 * np.pi * creak_freq * t) * noise * 0.3
    env = _envelope(t, attack=0.02, release=0.15)
    return _make_sound((rumble + creak) * env * 0.7)


def _gen_menu_select():
    """Menu tanlash — qisqa sine click"""
    t = _time_array(0.08)
    sig = np.sin(2 * np.pi * 1000 * t) * np.exp(-t * 50)
    return _make_sound(sig * 0.5)


def _gen_pause():
    """Pause — pastga sweep"""
    t = _time_array(0.15)
    freq = 800 - 500 * (t / 0.15)
    sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 15)
    return _make_sound(sig * 0.5)


def _gen_footstep():
    """Qadam ovozi — bass thump + noise"""
    t = _time_array(0.1)
    thump = np.sin(2 * np.pi * 100 * t) * np.exp(-t * 35)
    noise = np.random.uniform(-1, 1, len(t)).astype(np.float32) * np.exp(-t * 40)
    return _make_sound((thump * 0.6 + noise * 0.3) * 0.5)


def _gen_ambient():
    """Ambient muzika — drone: 55+82.5+110Hz, sekin modulatsiya (8 soniya loop)"""
    t = _time_array(8.0)
    # Uch qatlam drone
    d1 = np.sin(2 * np.pi * 55 * t)
    d2 = np.sin(2 * np.pi * 82.5 * t) * 0.7
    d3 = np.sin(2 * np.pi * 110 * t) * 0.5
    # Sekin modulatsiya
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t)
    # Past chastotali noise qatlam
    noise_len = len(t)
    noise = np.random.uniform(-0.1, 0.1, noise_len).astype(np.float32)
    # Oddiy low-pass: running average
    kernel_size = 200
    if noise_len > kernel_size:
        kernel = np.ones(kernel_size, dtype=np.float32) / kernel_size
        noise = np.convolve(noise, kernel, mode='same').astype(np.float32)
    sig = (d1 + d2 + d3) * mod * 0.25 + noise * 0.3
    # Crossfade uchun boshi va oxiri smooth
    fade = min(int(0.5 * SR), noise_len // 4)
    if fade > 0:
        sig[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
        sig[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    return _make_sound(sig * AUDIO_MUSIC_VOLUME / AUDIO_MASTER_VOLUME)


class SoundManager:
    """
    Protsedural ovozlarni boshqarish.
    Barcha ovozlar init paytida generatsiya qilinadi.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.sounds = {}
        self.music_channel = None
        self.footstep_timer = 0.0
        self.footstep_interval = AUDIO_FOOTSTEP_INTERVAL
        self.enabled = True

        self._generate_all_sounds()

    def _generate_all_sounds(self):
        """Barcha 18 ta ovozni generatsiya qilish"""
        generators = {
            'shoot': _gen_shoot,
            'reload': _gen_reload,
            'empty_click': _gen_empty_click,
            'enemy_death': _gen_enemy_death,
            'hit_marker': _gen_hit_marker,
            'player_damage': _gen_player_damage,
            'boss_start': _gen_boss_start,
            'boss_defeated': _gen_boss_defeated,
            'level_complete': _gen_level_complete,
            'game_over': _gen_game_over,
            'powerup': _gen_powerup,
            'trap': _gen_trap,
            'key_pickup': _gen_key_pickup,
            'door_open': _gen_door_open,
            'menu_select': _gen_menu_select,
            'pause': _gen_pause,
            'footstep': _gen_footstep,
            'ambient': _gen_ambient,
        }
        for name, gen_func in generators.items():
            try:
                self.sounds[name] = gen_func()
            except Exception as e:
                print(f"Sound generation error [{name}]: {e}")

        # SFX volume
        for name, snd in self.sounds.items():
            if name != 'ambient':
                snd.set_volume(AUDIO_SFX_VOLUME)

    def play(self, name):
        """Ovoz ijro etish"""
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.play()

    def play_music(self):
        """Ambient muzika loop boshlash"""
        if not self.enabled:
            return
        snd = self.sounds.get('ambient')
        if snd:
            self.music_channel = snd.play(loops=-1)

    def stop_music(self):
        """Ambient muzikani to'xtatish"""
        if self.music_channel:
            self.music_channel.stop()
            self.music_channel = None

    def update_footsteps(self, dt, is_moving):
        """Qadam ovoz loopini yangilash"""
        if not self.enabled:
            return
        if is_moving:
            self.footstep_timer -= dt
            if self.footstep_timer <= 0:
                self.play('footstep')
                self.footstep_timer = self.footstep_interval
        else:
            self.footstep_timer = 0.0
