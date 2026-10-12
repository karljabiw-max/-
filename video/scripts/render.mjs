// 逐帧渲染 index.html 的 window.render(t)，分段并行，直接管道进 ffmpeg 编码。
// 用法：
//   node scripts/render.mjs --out build/video.mp4 [--fps 30] [--workers 4]
//   node scripts/render.mjs --stills 3,30,46,70 --outdir build/stills   # 只出静帧
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') && a.push([v.slice(2), arr[i + 1]]), a), []));
const fps = +(args.fps || 30);
const workers = +(args.workers || 4);

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => console.error('[页面错误]', e.message));
  await page.goto('file://' + resolve(root, 'index.html'));
  await page.evaluate(() => { window.__RENDER_MODE__ = true; return window.setup(); });
  return page;
}
const shot = page => page.locator('#c').screenshot({ type: 'png' });

const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--disable-lcd-text'] });

if (args.stills) {
  const outdir = resolve(args.outdir || 'build/stills');
  mkdirSync(outdir, { recursive: true });
  const page = await openPage(browser);
  for (const s of args.stills.split(',').map(Number)) {
    await page.evaluate(t => window.render(t), s);
    writeFileSync(`${outdir}/t${String(s.toFixed(1)).padStart(5, '0')}.png`, await shot(page));
  }
  await browser.close();
  process.exit(0);
}

const out = resolve(args.out || 'build/video.mp4');
mkdirSync(dirname(out), { recursive: true });
const probe = await openPage(browser);
const dur = await probe.evaluate(() => window.DURATION);
await probe.close();
const total = Math.round(dur * fps);
const per = Math.ceil(total / workers);
const t0 = Date.now();
let done = 0;

const segs = await Promise.all(Array.from({ length: workers }, async (_, w) => {
  const a = w * per, b = Math.min(total, a + per);
  const seg = `${out}.seg${w}.mp4`;
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const page = await openPage(browser);
  for (let f = a; f < b; f++) {
    await page.evaluate(t => window.render(t), f / fps);
    const buf = await shot(page);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (++done % 300 === 0) console.log(`  ${done}/${total} 帧  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => c ? rej(new Error('ffmpeg ' + c)) : res()));
  return seg;
}));
await browser.close();

const list = `${out}.txt`;
writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out], { stdio: 'inherit' })
  .on('close', c => c ? rej(new Error('concat ' + c)) : res()));
console.log(`完成：${total} 帧 → ${out}（${((Date.now() - t0) / 1000).toFixed(0)}s）`);
