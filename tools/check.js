/* Smoke-test every page in headless Chromium: console errors, failed requests, rendered content. */
const { chromium } = require('playwright');

const BASE = 'http://127.0.0.1:8899/';
const PAGES = [
  ['index.html', '#brief h2'],
  ['archive.html', '#list article'],
  ['days.html', '#list article.day'],
  ['people.html', '#grid a.pcard'],
  ['person.html?id=fadiel-adams', '#profile h2'],
  ['map.html', '#graph .nodes g'],
  ['timeline.html', '#tl .ev'],
  ['methodology.html', '#gaps .card'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  let fail = 0;
  for (const [path, sel] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    const errs = [], bad = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
    page.on('requestfailed', r => bad.push(r.url() + ' ' + (r.failure() || {}).errorText));
    page.on('response', r => { if (r.status() >= 400) bad.push(r.url() + ' HTTP ' + r.status()); });

    await page.goto(BASE + path, { waitUntil: 'networkidle' });
    let count = 0;
    try { await page.waitForSelector(sel, { timeout: 6000 }); count = await page.locator(sel).count(); }
    catch (e) { errs.push('SELECTOR MISS: ' + sel); }

    // check nothing external is being pulled in
    const ext = bad.concat(await page.evaluate(() =>
      performance.getEntriesByType('resource').map(r => r.name).filter(n => !n.startsWith(location.origin))));

    const ok = !errs.length && !bad.length;
    if (!ok) fail++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${path.padEnd(30)} ${sel} → ${count}`);
    errs.slice(0, 4).forEach(e => console.log('        err: ' + e.slice(0, 190)));
    bad.slice(0, 4).forEach(e => console.log('        req: ' + e.slice(0, 190)));
    if (ext.length) console.log('        EXTERNAL: ' + ext.join(', ').slice(0, 200));

    const shot = path.split(/[?#.]/)[0];
    await page.screenshot({ path: `/tmp/shot-${shot}.png`, fullPage: false });
    await ctx.close();
  }

  // mobile pass on the two heaviest pages
  for (const path of ['index.html', 'map.html']) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push(e.message));
    await page.goto(BASE + path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    console.log(`${!overflow && !errs.length ? 'PASS' : 'FAIL'}  mobile 390px ${path} horizontal-overflow=${overflow}`);
    if (overflow || errs.length) fail++;
    await page.screenshot({ path: `/tmp/mob-${path.split('.')[0]}.png` });
    await ctx.close();
  }

  // light theme render
  const ctx = await browser.newContext();
  const p2 = await ctx.newPage();
  await p2.goto(BASE + 'days.html', { waitUntil: 'networkidle' });
  await p2.click('#theme-btn');
  await p2.waitForTimeout(400);
  const theme = await p2.evaluate(() => document.documentElement.getAttribute('data-theme'));
  console.log(`${theme === 'light' ? 'PASS' : 'FAIL'}  theme toggle → ${theme}`);
  await p2.screenshot({ path: '/tmp/shot-light.png' });
  await ctx.close();

  await browser.close();
  console.log(fail ? `\n${fail} FAILURES` : '\nAll checks passed.');
  process.exit(fail ? 1 : 0);
})();
