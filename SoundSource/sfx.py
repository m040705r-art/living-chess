# Procedural sound effects for Living Chess (user: no free Asset Store packs fit -> "音も調整しながら生成する").
# Every sound is synthesised from waveforms and noise (numpy/scipy), seeded, so a re-run gives the same files.
#   python SoundSource/sfx.py            -> Assets/Chess/Audio/*.wav (+ WebPreview/sounds/*.wav)
#   python SoundSource/sfx.py clash_1    -> only the named sounds
# Tune a sound by editing its function below and re-running; Unity re-imports the wav.
import sys, os, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTS = [os.path.join(ROOT, "Assets", "Chess", "Audio"), os.path.join(ROOT, "WebPreview", "sounds")]

def t_(dur): return np.arange(int(dur * SR)) / SR
def noise(n, rng): return rng.standard_normal(n)
def band(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def low(x, f, order=2): return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)
def high(x, f, order=2): return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)
def env_exp(n, tau, attack=0.002):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-6)) * np.exp(-t / tau)
def pad(x, dur):
    out = np.zeros(int(dur * SR)); out[:min(len(x), len(out))] += x[:len(out)]; return out
def mix(*xs):
    n = max(len(x) for x in xs); out = np.zeros(n)
    for x in xs: out[:len(x)] += x
    return out
def reverb(x, rng, size=1.1, wet=0.25, damp=3000):
    """A cheap stone-arena room: convolve with decaying, darkened noise."""
    x = fade(x, 0, 0.04)   # the dry sound ends softly (cut-off ringing clicked at its end)
    n = int(size * SR)
    ir = low(noise(n, rng), damp) * np.exp(-np.arange(n) / SR / (size / 5))
    ir /= np.sqrt((ir ** 2).sum())
    wetx = fftconvolve(x, ir)[:len(x) + n]
    return mix(x * (1 - wet), wetx * wet)
def norm(x, peak=0.9):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x
def fade(x, a=0.002, b=0.02):
    na, nb = int(a * SR), int(b * SR)
    x = x.copy()
    if na: x[:na] *= np.linspace(0, 1, na)
    if nb: x[-nb:] *= np.linspace(1, 0, nb)
    return x
def loopable(x, xf=0.5):
    """Crossfade the tail into the head so the clip loops without a click."""
    n = int(xf * SR)
    head, tail = x[:n].copy(), x[-n:].copy()
    w = np.linspace(0, 1, n)
    out = x[:-n].copy()
    out[:n] = head * w + tail * (1 - w)
    return out

# ---------------------------------------------------------------- metal
def clash(seed):
    """Blade on blade: a hard transient, then inharmonic ringing partials that beat against each other."""
    rng = np.random.default_rng(seed)
    f0 = rng.uniform(950, 1500)
    t = t_(1.8)
    ring = np.zeros_like(t)
    for ratio, tau, amp in ((1, 0.45, 1), (2.32, 0.3, 0.7), (4.25, 0.18, 0.55), (6.63, 0.11, 0.4), (9.38, 0.07, 0.3)):
        for det in (1.0, 1.0 + rng.uniform(0.002, 0.006)):   # detuned pairs -> shimmering beats
            ring += amp * np.sin(2 * np.pi * f0 * ratio * det * t + rng.uniform(0, 6.28)) * np.exp(-t / (tau * rng.uniform(0.8, 1.2)))
    hitn = high(noise(int(0.03 * SR), rng), 2500) * env_exp(int(0.03 * SR), 0.006)
    scrape = band(noise(int(0.12 * SR), rng), 3000, 9000) * env_exp(int(0.12 * SR), 0.03) * 0.5
    x = mix(ring * 0.35, hitn * 1.2, scrape)
    return fade(norm(reverb(x, rng, 0.9, 0.22)), 0.0005, 0.05)

def draw(seed):
    """A dagger leaving its sheath: a rising scrape, ending in a light ring."""
    rng = np.random.default_rng(seed)
    n = int(0.45 * SR); t = np.arange(n) / SR
    sc = noise(n, rng)
    out = np.zeros(n)
    for i, (lo, hi) in enumerate(((2500, 4500), (3500, 6500), (5000, 9000))):   # the scrape climbs as the blade slides
        seg = band(sc, lo, hi) * np.clip(1 - abs(t / 0.32 - (0.2 + i * 0.3)) * 2.2, 0, 1)
        out += seg
    out *= np.where(t < 0.32, 1, np.exp(-(t - 0.32) / 0.02)) * 0.6
    tip = np.zeros(int(0.7 * SR)); tt = t_(0.7); f0 = rng.uniform(2200, 2600)
    for ratio, tau in ((1, 0.25), (2.4, 0.12), (4.1, 0.07)):
        tip += np.sin(2 * np.pi * f0 * ratio * tt) * np.exp(-tt / tau)
    x = mix(out, np.concatenate([np.zeros(int(0.3 * SR)), tip * 0.18]))
    return fade(norm(reverb(x, rng, 0.8, 0.2)))

# ---------------------------------------------------------------- motion and impacts
def swing(seed):
    """A fast cut through the air: noise swept up and down through a band-pass (Doppler-ish)."""
    rng = np.random.default_rng(seed)
    dur = rng.uniform(0.24, 0.32); n = int(dur * SR)
    src = noise(n, rng); out = np.zeros(n)
    blk = 256
    for i in range(0, n, blk):
        u = i / n
        fc = 350 + 1700 * np.sin(np.pi * u) ** 1.5
        seg = src[max(0, i - 1024):i + blk]
        y = band(seg, fc * 0.6, min(fc * 1.6, 18000))[-min(blk, n - i):]
        out[i:i + len(y)] = y * np.sin(np.pi * u) ** 2
    return fade(norm(out, 0.8), 0.003, 0.03)

def hit_stone(seed):
    """A killing blow on a stone statue: a heavy thump, a crack, grit."""
    rng = np.random.default_rng(seed)
    t = t_(0.6)
    f = 75 * np.exp(-t / 0.25) + 40
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    body = low(noise(len(t), rng), 1800) * np.exp(-t / 0.08)
    crack = np.zeros(len(t))
    for _ in range(6):
        k = int(rng.uniform(0, 0.05) * SR); m = int(0.008 * SR)
        crack[k:k + m] += high(noise(m, rng), 2000) * env_exp(m, 0.002) * rng.uniform(0.4, 1)
    grit = band(noise(len(t), rng), 1500, 6000) * np.exp(-t / 0.18) * 0.25
    x = mix(thump * 1.2, body * 0.8, crack * 0.9, grit)
    return fade(norm(reverb(x, rng, 1.2, 0.28)))

def thud(seed):
    """A footfall / landing on the stone board: soft and low."""
    rng = np.random.default_rng(seed)
    t = t_(0.25)
    x = mix(np.sin(2 * np.pi * (90 + 30 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.05),
            low(noise(len(t), rng), 900) * np.exp(-t / 0.04) * 0.7,
            band(noise(len(t), rng), 1200, 4000) * np.exp(-t / 0.02) * 0.15)
    return fade(norm(x, 0.7))

def crumble(seed):
    """A statue breaking up: a dense rain of stone grains thinning out over a low rumble."""
    rng = np.random.default_rng(seed)
    dur = 1.6; n = int(dur * SR); out = np.zeros(n)
    for _ in range(170):
        start = rng.uniform(0, 1) ** 1.8 * (dur - 0.1)
        m = int(rng.uniform(0.004, 0.03) * SR); k = int(start * SR)
        fc = rng.uniform(300, 3500)
        g = band(noise(m + 64, rng), fc * 0.7, min(fc * 1.5, 18000))[64:] * env_exp(m, m / SR / 3)
        out[k:k + m] += g[:len(out[k:k + m])] * rng.uniform(0.2, 1) * (1 - start / dur * 0.6)
    t = np.arange(n) / SR
    rumble = low(noise(n, rng), 160) * np.exp(-t / 0.5) * 2.0
    x = mix(out, rumble)
    return fade(norm(reverb(x, rng, 1.2, 0.3)))

# ---------------------------------------------------------------- magic
CHORD = (440.0, 554.4, 659.3, 880.0, 1108.7, 1318.5)   # A major, spread

def magic_charge(seed):
    """Power gathering: a rising, trembling chord with sparkles, swelling."""
    rng = np.random.default_rng(seed)
    dur = 1.7; t = t_(dur); n = len(t)
    glide = 0.82 + 0.18 * (t / dur) ** 0.7
    x = np.zeros(n)
    for f in CHORD:
        ph = 2 * np.pi * np.cumsum(f * glide * (1 + 0.003 * np.sin(2 * np.pi * rng.uniform(4, 7) * t))) / SR
        x += np.sin(ph) * (0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(5, 9) * t + rng.uniform(0, 6))) / len(CHORD)
    x *= (t / dur) ** 1.6
    sp = np.zeros(n)
    for _ in range(45):
        k = int(rng.uniform(0.1, 1) ** 0.6 * (n - 6000)); m = int(0.12 * SR)
        f = rng.uniform(2500, 6500); tt = np.arange(m) / SR
        sp[k:k + m] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.03) * 0.25 * (k / n)
    air = band(noise(n, rng), 3000, 9000) * (t / dur) ** 2 * 0.12
    return fade(norm(reverb(mix(x, sp, air), rng, 1.4, 0.35)), 0.05, 0.05)

def magic_burst(seed):
    """The spell lands: a deep boom under a bright chord flash that rings away, with sparkle."""
    rng = np.random.default_rng(seed)
    dur = 2.2; t = t_(dur); n = len(t)
    boom = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.35)
    blast = low(noise(n, rng), 2500) * np.exp(-t / 0.12) * 0.8
    shim = np.zeros(n)
    for f in CHORD + (1760.0, 2217.5):
        shim += np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 6 * t))) * np.exp(-t / rng.uniform(0.5, 0.9))
    shim *= 0.12
    sp = np.zeros(n)
    for _ in range(60):
        k = int(rng.uniform(0, 1) ** 2 * (n - 6000)); m = int(0.1 * SR); tt = np.arange(m) / SR
        sp[k:k + m] += np.sin(2 * np.pi * rng.uniform(3000, 8000) * tt) * np.exp(-tt / 0.025) * 0.15
    return fade(norm(reverb(mix(boom * 1.3, blast, shim, sp), rng, 1.8, 0.35)))

def lightning(seed):
    """A bolt: a whip-crack, a sizzling crackle, then a rolling low tail."""
    rng = np.random.default_rng(seed)
    dur = 1.4; t = t_(dur); n = len(t)
    crack = high(noise(n, rng), 1500) * env_exp(n, 0.012, 0.0005) * 1.5
    sizzle = np.zeros(n)
    k = 0
    while k < int(0.35 * SR):
        m = int(rng.uniform(0.001, 0.006) * SR)
        sizzle[k:k + m] += high(noise(m + 32, rng), 3000)[32:] * rng.uniform(0.2, 1)
        k += int(rng.exponential(0.008) * SR) + m
    roll = low(noise(n, rng), 220) * np.exp(-t / 0.45) * 2.2 * np.minimum(1, t / 0.05)
    return fade(norm(reverb(mix(crack, sizzle * 0.6, roll), rng, 1.5, 0.3)))

def shockwave(seed):
    """A heavy blow on the board: a falling sub boom with a gust of air."""
    rng = np.random.default_rng(seed)
    dur = 1.6; t = t_(dur); n = len(t)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 110 * np.exp(-t / 0.12)) / SR) * np.exp(-t / 0.5)
    gust = band(noise(n, rng), 200, 2500) * np.exp(-t / 0.3) * np.minimum(1, t / 0.03) * 0.5
    return fade(norm(reverb(mix(boom * 1.4, gust), rng, 1.6, 0.3)))

# ---------------------------------------------------------------- the arena
def _voices(rng, n, count, f_lo, f_hi, level_curve):
    """Many voices: sawtooth-ish tones with vibrato, through vowel formants, each fading in and out."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    formants = ((700, 1200), (400, 2000), (550, 900), (300, 2300), (600, 1700))
    for _ in range(count):
        f0 = rng.uniform(f_lo, f_hi)
        vib = 1 + 0.012 * np.sin(2 * np.pi * rng.uniform(4, 6.5) * t + rng.uniform(0, 6)) + 0.03 * np.sin(2 * np.pi * rng.uniform(0.1, 0.4) * t)
        ph = np.cumsum(f0 * vib) / SR
        saw = (ph % 1.0) * 2 - 1
        f1, f2 = formants[rng.integers(len(formants))]
        v = band(saw, f1 * 0.7, f1 * 1.3) + 0.6 * band(saw, f2 * 0.8, f2 * 1.2)
        a = np.clip(np.sin(2 * np.pi * rng.uniform(0.05, 0.3) * t + rng.uniform(0, 6.28)) * 0.8 + 0.4, 0, 1)
        out += v * a * rng.uniform(0.3, 1)
    return out * level_curve

def crowd_loop(seed):
    """The stands, always there: a murmur of many voices over a broad bed, looping seamlessly."""
    rng = np.random.default_rng(seed)
    dur = 12.5; n = int(dur * SR); t = np.arange(n) / SR
    bed = band(noise(n, rng), 250, 2500) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))
    v = _voices(rng, n, 70, 110, 320, 1.0)
    claps = np.zeros(n)
    for _ in range(140):   # scattered clapping and calls
        k = int(rng.uniform(0, dur - 0.05) * SR); m = int(0.012 * SR)
        claps[k:k + m] += band(noise(m, rng), 1000, 5000) * env_exp(m, 0.004) * rng.uniform(0.1, 0.5)
    x = mix(bed * 0.5, norm(v) * 0.6, claps)
    x = reverb(x, rng, 1.8, 0.45, 2500)[:n]
    return norm(loopable(x, 0.6), 0.6)

def crowd_cheer(seed):
    """The verdict: the stands roar up, hold, applaud and settle."""
    rng = np.random.default_rng(seed)
    dur = 4.5; n = int(dur * SR); t = np.arange(n) / SR
    swell = np.clip(t / 0.35, 0, 1) * np.where(t < 2.2, 1, np.exp(-(t - 2.2) / 1.0))
    v = _voices(rng, n, 120, 160, 460, swell)
    roar = band(noise(n, rng), 300, 3500) * swell * 0.7
    claps = np.zeros(n)
    for _ in range(900):
        s = rng.uniform(0.3, dur - 0.05); k = int(s * SR); m = int(0.01 * SR)
        claps[k:k + m] += band(noise(m, rng), 900, 6000) * env_exp(m, 0.003) * rng.uniform(0.2, 0.8) * np.clip((s - 0.3) / 0.6, 0, 1) * np.exp(-max(0, s - 2.5) / 1.2)
    x = mix(norm(v) * 0.8, roar, claps * 0.8)
    return fade(norm(reverb(x, rng, 1.8, 0.45, 2500)[:n], 0.85), 0.01, 0.4)

def fire_loop(seed):
    """A fire bowl: a soft roar with pops and crackles, looping seamlessly."""
    rng = np.random.default_rng(seed)
    dur = 8.5; n = int(dur * SR); t = np.arange(n) / SR
    roar = low(np.cumsum(noise(n, rng)) * 0.02, 400) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t))
    roar -= low(roar, 30)
    cr = np.zeros(n)
    for _ in range(150):
        k = int(rng.uniform(0, dur - 0.02) * SR); m = int(rng.uniform(0.001, 0.008) * SR)
        cr[k:k + m] += high(noise(m + 32, rng), 1500)[32:] * rng.uniform(0.05, 1) ** 3 * 0.7
    x = mix(norm(roar) * 0.5, cr)
    return norm(loopable(x, 0.4), 0.55)

SOUNDS = {
    **{f"clash_{i}": (clash, 10 + i) for i in range(1, 4)},
    **{f"swing_{i}": (swing, 20 + i) for i in range(1, 4)},
    **{f"hit_{i}": (hit_stone, 30 + i) for i in range(1, 3)},
    **{f"thud_{i}": (thud, 40 + i) for i in range(1, 3)},
    "draw": (draw, 50), "crumble": (crumble, 60),
    "magic_charge": (magic_charge, 70), "magic_burst": (magic_burst, 71), "lightning": (lightning, 72), "shockwave": (shockwave, 73),
    "crowd_loop": (crowd_loop, 80), "crowd_cheer": (crowd_cheer, 81), "fire_loop": (fire_loop, 82),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(SOUNDS)
    for d in OUTS: os.makedirs(d, exist_ok=True)
    for name in names:
        fn, seed = SOUNDS[name]
        x = np.clip(fn(seed), -1, 1)
        data = (x * 32767).astype(np.int16)
        for d in OUTS: wavfile.write(os.path.join(d, name + ".wav"), SR, data)
        print(f"{name:14s} {len(x) / SR:5.2f}s  peak {np.abs(x).max():.2f}")
