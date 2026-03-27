const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('https://help.sap.com/docs/joule/capabilities-guide/transactional-capabilities', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 800));
  const info = await page.evaluate(() => {
    const body = document.querySelector('.body') || document.querySelector('main') || document.body;
    const h2s = [...body.querySelectorAll('h2')].map(h => h.innerText.replace(/[^\x00-\x7F]/g,'').trim());
    const paras = [...body.querySelectorAll('p')].map(p => p.innerText.trim()).filter(t => t.length > 20);
    const tables = [...body.querySelectorAll('table')].map(t => {
      const rows = t.querySelectorAll('tr').length;
      const headers = [...t.querySelectorAll('thead th, tr:first-child th, tr:first-child td')].map(c => c.innerText.trim());
      const sample = [...t.querySelectorAll('tbody tr')].slice(0,3).map(r =>
        [...r.querySelectorAll('td,th')].map(c => c.innerText.trim().substring(0,80))
      );
      return { rows, headers, sample };
    });
    const lists = [...body.querySelectorAll('ul li, ol li')].map(li => li.innerText.trim()).filter(t => t.length > 5 && t.length < 300).slice(0,15);
    return { h2s, paras, tables, lists, url: window.location.href };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})().catch(console.error);
