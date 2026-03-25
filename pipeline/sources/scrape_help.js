/**
 * Scrape SAP Help Portal Joule Capabilities Guide
 * Extracts Use Case tables (Use Case, Example Prompts, Joule Response)
 * from each capability page.
 *
 * Usage: node pipeline/sources/scrape_help.js
 * Output: pipeline/data/scraped_use_cases.json
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://help.sap.com/docs/joule/capabilities-guide/';
const TOC_FILE = path.join(__dirname, 'toc_tree.txt');
const OUT_FILE = path.join(__dirname, '..', 'data', 'scraped_use_cases.json');

// Parse the TOC tree to get leaf slugs
function parseTOC() {
  const lines = fs.readFileSync(TOC_FILE, 'utf8').split('\n');
  const entries = [];
  const pathStack = [];

  for (const line of lines) {
    if (!line.trim()) continue;
    const stripped = line.trimStart();
    const indent = line.length - stripped.length;
    const depth = Math.floor(indent / 2);
    const title = stripped.trim();

    while (pathStack.length > depth) pathStack.pop();
    pathStack.push(title);

    entries.push({ title, depth, path: [...pathStack] });
  }

  // Find leaves (entries with no children)
  const leaves = [];
  for (let i = 0; i < entries.length; i++) {
    const isLeaf = i === entries.length - 1 || entries[i + 1].depth <= entries[i].depth;
    if (isLeaf) {
      leaves.push(entries[i]);
    }
  }
  return leaves;
}

function titleToSlug(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
}

// Skip config/admin pages
const SKIP_PATTERNS = [
  /what's new/i, /archive/i, /activating/i, /multi language/i,
  /glossary/i, /important notes/i, /initial setup/i,
  /release-specific/i, /configuring/i, /configuration/i,
];

async function scrapePage(browser, url, title) {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 20000 });

    // Wait for content to render
    await page.waitForSelector('table, .section, h1', { timeout: 10000 }).catch(() => {});

    // Extract tables with use case data
    const data = await page.evaluate(() => {
      const result = {
        description: '',
        useCases: [],
        prerequisites: [],
      };

      // Get page description (first paragraph)
      const firstP = document.querySelector('.topic-content p, .section p, article p');
      if (firstP) {
        result.description = firstP.textContent.trim();
      }

      // Find all tables
      const tables = document.querySelectorAll('table');
      for (const table of tables) {
        const headers = [...table.querySelectorAll('thead th, tr:first-child th')]
          .map(th => th.textContent.trim().toLowerCase());

        // Check if this is a use case table
        const hasUseCase = headers.some(h => h.includes('use case'));
        const hasPrompts = headers.some(h => h.includes('prompt') || h.includes('example'));
        const hasResponse = headers.some(h => h.includes('response') || h.includes('joule'));

        if (hasUseCase || hasPrompts) {
          const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
          for (const row of rows) {
            const cells = [...row.querySelectorAll('td')];
            if (cells.length >= 2) {
              const useCase = {
                name: cells[0] ? cells[0].textContent.trim() : '',
                prompts: [],
                response: '',
              };

              // Extract prompts (might be in cell 1 or cell with "prompt" header)
              const promptCell = cells[1];
              if (promptCell) {
                // Split by line breaks or periods to get individual prompts
                const text = promptCell.innerText || promptCell.textContent;
                const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 5);
                useCase.prompts = lines;
              }

              // Extract response
              if (cells.length >= 3) {
                useCase.response = cells[2] ? cells[2].textContent.trim().substring(0, 500) : '';
              }

              if (useCase.name || useCase.prompts.length > 0) {
                result.useCases.push(useCase);
              }
            }
          }
        }

        // Check for prerequisites table
        const hasPrereq = headers.some(h => h.includes('prerequisite') || h.includes('role'));
        if (hasPrereq) {
          const rows = table.querySelectorAll('tbody tr');
          for (const row of rows) {
            const cells = [...row.querySelectorAll('td')];
            if (cells.length > 0) {
              result.prerequisites.push(cells[0].textContent.trim());
            }
          }
        }
      }

      // Also look for bullet lists of prompts (some pages use lists instead of tables)
      if (result.useCases.length === 0) {
        const listItems = document.querySelectorAll('ul li, ol li');
        const promptLike = [];
        for (const li of listItems) {
          const text = li.textContent.trim();
          // Prompts often start with verbs like "Show", "Display", "Create", etc.
          if (/^(show|display|create|manage|find|search|open|what|how|list|get|check)/i.test(text) && text.length < 200) {
            promptLike.push(text);
          }
        }
        if (promptLike.length > 0) {
          result.useCases.push({
            name: 'General',
            prompts: promptLike,
            response: '',
          });
        }
      }

      // Extract prerequisite roles from bullet lists
      if (result.prerequisites.length === 0) {
        const allLIs = document.querySelectorAll('li');
        for (const li of allLIs) {
          const text = li.textContent.trim();
          if (/^SAP_BR_|^SAP_/.test(text) && text.length < 100) {
            result.prerequisites.push(text);
          }
        }
      }

      return result;
    });

    await page.close();
    return data;
  } catch (err) {
    console.error(`  ✗ Error scraping ${title}: ${err.message}`);
    await page.close();
    return { description: '', useCases: [], prerequisites: [], error: err.message };
  }
}

async function main() {
  console.log('🔍 Scraping SAP Help Portal — Joule Capabilities Guide');
  console.log('');

  const leaves = parseTOC();
  console.log(`   Found ${leaves.length} leaf entries in TOC`);

  // Filter out skip patterns
  const toScrape = leaves.filter(e => !SKIP_PATTERNS.some(p => p.test(e.title)));
  console.log(`   After filtering: ${toScrape.length} pages to scrape`);
  console.log('');

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const results = {};
  let scraped = 0;
  let withUseCases = 0;

  for (const entry of toScrape) {
    const slug = titleToSlug(entry.title);
    const url = BASE_URL + slug;

    process.stdout.write(`   [${++scraped}/${toScrape.length}] ${entry.title}...`);

    const data = await scrapePage(browser, url, entry.title);
    data.title = entry.title;
    data.slug = slug;
    data.url = url;
    data.path = entry.path;

    results[entry.title] = data;

    if (data.useCases.length > 0) {
      withUseCases++;
      const promptCount = data.useCases.reduce((s, uc) => s + uc.prompts.length, 0);
      console.log(` ✓ ${data.useCases.length} use cases, ${promptCount} prompts`);
    } else {
      console.log(' (no table found)');
    }

    // Small delay to be nice to SAP servers
    await new Promise(r => setTimeout(r, 500));
  }

  await browser.close();

  // Write output
  const outDir = path.dirname(OUT_FILE);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const output = {
    metadata: {
      scraped_at: new Date().toISOString(),
      total_pages: toScrape.length,
      pages_with_use_cases: withUseCases,
      source: 'https://help.sap.com/docs/joule/capabilities-guide/',
    },
    pages: results,
  };

  fs.writeFileSync(OUT_FILE, JSON.stringify(output, null, 2));

  console.log('');
  console.log(`✅ Scraped ${scraped} pages`);
  console.log(`   ${withUseCases} pages with use case tables`);
  console.log(`   💾 Saved to ${OUT_FILE}`);
}

main().catch(console.error);