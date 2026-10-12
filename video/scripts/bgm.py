#!/usr/bin/env python3
"""《不》配乐：numpy 合成，77 BPM，A 小调。段落与分镜对齐。
用法: python3 scripts/bgm.py build/bgm.wav [--plot build/bgm.png]
"""
import sys, wave
import numpy as np

SR = 44100
DUR = 135.0
BPM = 77
BEAT = 60 / BPM
BAR = BEAT * 4
N = int(SR * (DUR + 4))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(3)

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def midi(s):  # 'A4' -> 69
    return NOTE[s[:-1]] + 12 * (int(s[-1]) + 1)

def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2)
    R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)

def env(n, a, d_tau, rel=0.05):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d_tau)
    r = int(rel * SR)
    if r and n > r: e[-r:] *= np.linspace(1, 0, r)
    return e

def piano(m, dur=2.5, vel=.5):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + .0004 * k * k)) * (.6 ** (k - 1)) * np.exp(-t * (1.2 + k * .9)) for k in range(1, 7))
    return s * env(n, .004, 1.6) * vel

def musicbox(m, dur=2.0, vel=.35):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * f * 4.01 * t) * np.exp(-t * 6) + .15 * np.sin(2 * np.pi * f * 2 * t)
    return s * env(n, .002, .7) * vel

def pad(ms, dur, vel=.12, att=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for m in ms:
        f = hz(m)
        for det in (-.12, .0, .11):
            ff = f * 2 ** (det / 12 / 4)
            s += sum(np.sin(2 * np.pi * ff * k * t + k) / k ** 1.6 for k in range(1, 5))
    e = np.minimum(1, t / att) * np.minimum(1, (dur - t) / att)
    return s * e * vel / len(ms)

def bass(m, dur, vel=.32):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 2 * f * t)
    return s * np.minimum(1, t / .02) * np.minimum(1, (dur - t) / .15) * np.exp(-t * .4) * vel

def kick(vel=.5):
    n = int(.4 * SR); t = np.arange(n) / SR
    f = 42 + 50 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * vel

def shaker(vel=.05):
    n = int(.09 * SR); x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))  # 高通
    return x * np.exp(-np.arange(n) / SR * 45) * vel

def bell(m, vel=.4, dur=5):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in [(1, 1, .6), (2.76, .5, 1.3), (5.4, .25, 2.4), (8.93, .12, 4)])
    return s * env(n, .002, 3) * vel

# 和弦（midi 列表）
CH = {
    'Am': ['A3', 'C4', 'E4'], 'F': ['F3', 'A3', 'C4'], 'C': ['C4', 'E4', 'G4'], 'G': ['G3', 'B3', 'D4'],
    'Fmaj7': ['F3', 'A3', 'C4', 'E4'], 'Em': ['E3', 'G3', 'B3'], 'Dm': ['D3', 'F3', 'A3'], 'Esus': ['E3', 'A3', 'B3'],
}
ROOT = {'Am': 'A2', 'F': 'F2', 'C': 'C3', 'G': 'G2', 'Fmaj7': 'F2', 'Em': 'E2', 'Dm': 'D2', 'Esus': 'E2'}

# 段落：(起, 止, 和弦进行, 配置)
SECTIONS = [
    (0.0, 14.5, ['Am', 'F', 'C', 'G'], dict(pad=.10, box=True)),
    (14.5, 20.5, ['F', 'G'], dict(pad=.16, piano=.45, bass=True, bell='A5')),
    (20.5, 52.0, ['Am', 'F', 'C', 'G'], dict(pad=.12, piano=.38, bass=True, box=.6)),
    (52.0, 80.0, ['Am', 'F', 'C', 'G'], dict(pad=.12, piano=.36, bass=True, kick=.35, shaker=True, arp=True)),
    (80.0, 88.0, ['Dm', 'Esus'], dict(pad=.14, piano=.4, bass=True, kick=.42, shaker=True, arp=True)),
    (88.0, 104.0, ['Fmaj7', 'G', 'Em', 'Am'], dict(pad=.14, piano=.42, bass=True, box=.5, kick=.25)),
    (104.0, 116.0, ['C', 'G', 'Am', 'F'], dict(pad=.12, piano=.36, bass=True, box=.7, kick=.25, shaker=True)),
    (116.0, 124.0, ['F', 'G', 'Am', 'Am'], dict(pad=.18, piano=.5, bass=True, arp=True, bell='E6', bell_t=120.0)),
    (124.0, 135.0, ['F', 'Am', 'F', 'Am'], dict(pad=.10, piano=.28, outro=True)),
]
MOTIF = ['E5', 'G5', 'A5', 'G5', 'E5', 'D5', 'C5', 'D5']  # 童谣感的小动机（A 小调五声）

for a, b, prog, cfg in SECTIONS:
    nbars = int(np.ceil((b - a) / BAR - 1e-6))
    barlen = (b - a) / nbars  # 让和弦变化正好落在段落边界
    for i in range(nbars):
        t0 = a + i * barlen
        ch = prog[i % len(prog)]
        ms = [midi(x) for x in CH[ch]]
        add(pad(ms + [ms[0] + 12], barlen + 1.2, cfg['pad']), t0, 0)
        if cfg.get('bass'): add(bass(midi(ROOT[ch]), barlen), t0, 0)
        if cfg.get('piano'):
            add(sum(np.pad(piano(m, 3.2, cfg['piano'] / 3), (int(k * .018 * SR), 0))[: int(3.2 * SR)] for k, m in enumerate(ms)), t0, -.15)
            if cfg.get('outro') and i % 2 == 1: add(piano(midi('E5'), 4, .18), t0 + barlen / 2, .3)
        bt = barlen / 4
        if cfg.get('kick'):
            for k in (0, 2): add(kick(cfg['kick']), t0 + k * bt)
        if cfg.get('shaker'):
            for k in range(8): add(shaker(.04 if k % 2 else .025), t0 + k * bt / 2, .4)
        if cfg.get('arp'):
            seq = ms + [ms[1] + 12, ms[2] + 12, ms[0] + 12, ms[2]]
            for k in range(8): add(piano(seq[k % len(seq)] + 12, 1.2, .07), t0 + k * bt / 2, .35 * (1 if k % 2 else -1))
        if cfg.get('box'):
            v = cfg['box'] if isinstance(cfg['box'], float) else 1.0
            if i % 2 == 0 or a == 0:
                for k in range(4): add(musicbox(midi(MOTIF[(i * 4 + k) % 8]), 2.0, .2 * v), t0 + k * bt, .5)
    if cfg.get('bell'): add(bell(midi(cfg['bell']), .22), cfg.get('bell_t', a), 0)

# 关键点缀：「不！」三连（7.6/8.6/9.7 秒附近）、哭闹（85.0）、「我」（48.4）
for tt in (8.05, 9.1, 10.15): add(musicbox(midi('A5'), 1.0, .22), tt, .2)
add(bell(midi('A5'), .18), 48.4, 0)
add(kick(.55), 85.0)

# 简易混响：指数衰减噪声脉冲响应
def reverb(x, sec=2.4, mix=.28):
    n = int(sec * SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.0); ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum())
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x * (1 - mix) + y * mix * 1.6

L, R = reverb(L), reverb(R)
st = np.stack([L, R], 1)[: int(DUR * SR)]
fade = int(3.0 * SR); st[-fade:] *= np.linspace(1, 0, fade)[:, None]
st[: int(.05 * SR)] *= np.linspace(0, 1, int(.05 * SR))[:, None]
st /= np.abs(st).max() / .89

out = sys.argv[1]
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())

# 波形自检（听不到，就看）
rms = np.sqrt(np.convolve((st ** 2).mean(1), np.ones(SR) / SR, 'valid')[::SR // 2])
print('峰值', round(float(np.abs(st).max()), 3), '每半秒 RMS 最小/最大', round(float(rms.min()), 4), round(float(rms.max()), 4))
quiet = [i / 2 for i, v in enumerate(rms) if v < .01]
print('静音段(秒):', quiet[:10], '...' if len(quiet) > 10 else '')
if '--plot' in sys.argv:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.figure(figsize=(16, 3)); plt.plot(np.arange(len(rms)) / 2, rms)
    for a, *_ in SECTIONS: plt.axvline(a, color='r', lw=.5)
    plt.savefig(sys.argv[sys.argv.index('--plot') + 1], dpi=80)
