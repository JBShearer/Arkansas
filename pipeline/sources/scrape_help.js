/**
 * Scrape SAP Help Portal Joule Capabilities Guide
 * Extracts Use Case tables (Use Case, Example Prompts, Joule Response)
 * from each capability page.
 *
 * Usage: node pipeline/sources/scrape_help.js
 * Output: pipeline/data/scraped_use_cases.json
 *
 * Key design principles:
 *   1. All extraction is scoped to the main content area — never the sidebar.
 *   2. Tables with >100 rows are rejected as navigation/sidebar tables.
 *   3. List fallback only triggers when the list is inside main content.
 *   4. Any batch of prompts containing "What's New" is discarded.
 *   5. Rows where the name is literally a capability type are handled as
 *      Ariba-style misaligned tables (type in col 2, description in col 3).
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
  /requesting access to sap business technology platform/i,
];

// URL overrides for pages where the slug doesn't match the TOC title
// (SAP renamed pages without redirect)
const URL_OVERRIDES = {
  'joule-in-sap-signavio-process-transformation-suite':
    'https://help.sap.com/docs/joule/capabilities-guide/joule-in-sap-signavio-process-transformation-suite',
  'searching-for-outbound-delivery-orders':
    'https://help.sap.com/docs/joule/capabilities-guide/querying-outbound-delivery-orders',
};

async function scrapePage(browser, url, title) {
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

    // Wait for main content to appear — prefer article/main over generic table
    await page.waitForSelector(
      'article, [role="main"], .topic-content, main, table, h1',
      { timeout: 15000 }
    ).catch(() => {});

    // Small extra wait for lazy-rendered JS content
    await new Promise(r => setTimeout(r, 300));

    const data = await page.evaluate(() => {
      const result = {
        description: '',
        useCases: [],
        prerequisites: [],
      };

      // ── 1. Locate the main content area ────────────────────────────────────
      // SAP Help renders a left sidebar (TOC nav) and a right main content zone.
      // We must restrict all extraction to the main content zone to avoid
      // picking up sidebar navigation tables and lists.
      const contentArea = (
        document.querySelector('article') ||
        document.querySelector('[role="main"]') ||
        document.querySelector('.topic-content') ||
        document.querySelector('.helpContent') ||
        document.querySelector('.body') ||
        document.querySelector('main') ||
        // Last resort: find the div that contains a <table> but is NOT in a nav/aside
        (() => {
          const tables = document.querySelectorAll('table');
          for (const t of tables) {
            let el = t.parentElement;
            while (el && el !== document.body) {
              const tag = el.tagName.toLowerCase();
              const role = (el.getAttribute('role') || '').toLowerCase();
              if (tag === 'nav' || tag === 'aside' || role === 'navigation') break;
              if (tag === 'article' || tag === 'main' || el.classList.contains('topic-content')) {
                return el;
              }
              el = el.parentElement;
            }
          }
          return null;
        })() ||
        document.body
      );

      // ── 2. Get page description from main content ───────────────────────────
      // Use the first substantive paragraph (skip very short ones that are
      // just "Learn about..." navigation stubs).
      const allParas = contentArea.querySelectorAll('p');
      for (const p of allParas) {
        const text = p.textContent.trim().replace(/\s+/g, ' ');
        if (text.length > 40) {
          result.description = text;
          break;
        }
      }

      // ── 3. Extract tables ───────────────────────────────────────────────────
      const tables = contentArea.querySelectorAll('table');

      for (const table of tables) {
        const allRows = table.querySelectorAll('tr');

        // Reject sidebar/navigation tables: too many rows
        if (allRows.length > 100) continue;

        const headers = [...table.querySelectorAll('thead th, tr:first-child th, tr:first-child td')]
          .map(th => (th.innerText || th.textContent || '').trim().toLowerCase());

        const hasUseCase = headers.some(h => h.includes('use case'));
        const hasPrompts = headers.some(h => h.includes('prompt') || h.includes('example'));
        const hasResponse = headers.some(h =>
          h.includes('response') || h.includes('joule') || h.includes('description')
        );

        // Accept table if it has any relevant header, OR has ≥2 columns and some content
        const isUseCaseTable = hasUseCase || hasPrompts || hasResponse;
        const couldBeUseCaseTable = !isUseCaseTable && headers.length >= 2;

        if (!isUseCaseTable && !couldBeUseCaseTable) continue;

        const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');

        for (const row of rows) {
          const cells = [...row.querySelectorAll('td, th')];
          if (cells.length < 2) continue;

          const name = cells[0] ? (cells[0].innerText || cells[0].textContent || '').trim() : '';

          // Skip rows with empty name or name that looks like a sidebar nav item
          if (!name) continue;
          if (name === 'Joule' || name === 'SAP' || name.startsWith('What\'s New')) continue;
          // Skip rows that look like column headers (short text, title-case, no spaces common in data)
          const looksLikeHeader = cells.every(c => {
            const t = (c.innerText || c.textContent || '').trim();
            return t.length < 40 && !/\d/.test(t);
          }) && cells[0].tagName.toLowerCase() === 'th';
          if (looksLikeHeader) continue;
          // Skip rows where all cells are very short (likely a separator or header row)
          const totalText = cells.map(c => (c.innerText || c.textContent || '').trim()).join('').length;
          if (totalText < 5) continue;

          const useCase = { name, prompts: [], response: '', cells: [] };

          // Store all cell values for tables with non-standard column layouts
          useCase.cells = cells.map(c => (c.innerText || c.textContent || '').trim());

          // Extract prompts from cell[1]
          const promptCell = cells[1];
          if (promptCell) {
            const text = (promptCell.innerText || promptCell.textContent || '').trim();
            const lines = text.split('\n')
              .map(l => l.trim())
              .filter(l => l.length > 5);
            // Reject if these look like sidebar nav items
            const hasSidebarSignal = lines.some(l =>
              l.startsWith("What's New") || l === 'Cloud Foundry' || l === 'SAP BTP'
            );
            if (!hasSidebarSignal) {
              useCase.prompts = lines;
            }
          }

          // Extract response/description from cell[2]
          const responseCell = cells.length >= 3 ? cells[2] : null;
          if (responseCell) {
            useCase.response = (responseCell.innerText || responseCell.textContent || '').trim().substring(0, 500);
          }

          if (useCase.name || useCase.prompts.length > 0) {
            result.useCases.push(useCase);
          }
        }
      }

      // ── 4a. h2-scoped extraction: "Examples" / "Use Cases" sections ──────────
      // Many pages use an <h2>Examples</h2> or <h2>Use Cases</h2> heading
      // followed by <li> items that are the actual sample prompts.
      // This is unambiguous — collect everything between the heading and
      // the next sibling heading as prompts for a use case named after the page title.
      // NOTE: SAP Help h2 elements contain a <span> + icon <button>, so we use
      // innerText (strips icon font chars) and includes() not strict equality.
      if (result.useCases.length === 0) {
        const headings = contentArea.querySelectorAll('h2, h3');
        for (const heading of headings) {
          const headText = (heading.innerText || heading.textContent || '').trim().toLowerCase();
          if (headText.includes('examples') || headText === 'use cases' || headText === 'example') {
            const prompts = [];
            let sibling = heading.nextElementSibling;
            while (sibling) {
              const tag = sibling.tagName.toLowerCase();
              // Stop at next heading
              if (['h1','h2','h3','h4'].includes(tag)) break;
              // Collect list items
              if (tag === 'ul' || tag === 'ol') {
                for (const li of sibling.querySelectorAll('li')) {
                  const text = (li.innerText || li.textContent || '').trim().replace(/\s+/g, ' ');
                  if (text.length >= 5 && text.length < 250) {
                    prompts.push(text);
                  }
                }
              }
              sibling = sibling.nextElementSibling;
            }
            if (prompts.length > 0) {
              result.useCases.push({ name: 'General', prompts, response: '' });
              break; // one Examples section per page is enough
            }
          }
        }
      }

      // ── 4b. Fallback: inline prose prompts ─────────────────────────────────
      // Some pages embed example prompts inline in <p> text:
      // "you can ask Joule to List outbound delivery order items for sales order 1234"
      // Extract the prompt fragment after "ask Joule to/ask Joule " from each paragraph.
      if (result.useCases.length === 0) {
        const proseParagraphs = contentArea.querySelectorAll('p');
        const extractedPrompts = [];
        for (const p of proseParagraphs) {
          const text = (p.innerText || p.textContent || '').trim();
          // Match "ask Joule to <prompt>" or "ask Joule <prompt>" (no "to")
          const matches = text.matchAll(/ask Joule(?:\s+to)?\s+([A-Z][^.?!]{10,150})/g);
          for (const m of matches) {
            const prompt = m[1].trim();
            // Basic sanity: ends with a sentence fragment, no sidebar-like text
            if (prompt.length > 10 && prompt.length < 200) {
              extractedPrompts.push(prompt);
            }
          }
        }
        if (extractedPrompts.length > 0) {
          result.useCases.push({ name: 'General', prompts: extractedPrompts, response: '' });
        }
      }

      // ── 4c. Fallback: bullet lists in main content ──────────────────────────
      // Only trigger when no table data AND no h2-scoped data was found.
      // Scoped strictly to contentArea to avoid sidebar nav lists.
      if (result.useCases.length === 0) {
        const listItems = contentArea.querySelectorAll('ul li, ol li');
        const promptLike = [];
        for (const li of listItems) {
          const text = li.textContent.trim();
          // Must start with an action verb and be a reasonable prompt length
          if (
            /^(show|display|create|manage|find|search|open|what|how|list|get|check|view|navigate|go to|change|update|delete|assign|approve|cancel|post|release)\b/i.test(text) &&
            text.length >= 10 &&
            text.length < 200 &&
            !text.startsWith("What's New") &&
            !text.match(/^\d{4}/)  // reject "2024 What's New..." date-prefixed items
          ) {
            promptLike.push(text);
          }
        }

        // Sanity check: reject if batch looks like sidebar TOC
        // (TOC items tend to be page titles that match other TOC entries, not user queries)
        const hasSidebarSignal = promptLike.some(p =>
          p.startsWith("What's New") ||
          p === 'Finding Apps with Navigational Capability' ||
          p === 'Display Business Partners' ||
          p.startsWith('Joule in SAP')
        );

        if (promptLike.length > 0 && !hasSidebarSignal && promptLike.length < 50) {
          result.useCases.push({
            name: 'General',
            prompts: promptLike,
            response: '',
          });
        }
      }

      // ── 5. Prerequisites ────────────────────────────────────────────────────
      const allLIs = contentArea.querySelectorAll('li');
      for (const li of allLIs) {
        const text = li.textContent.trim();
        if (/^SAP_BR_|^SAP_/.test(text) && text.length < 100) {
          result.prerequisites.push(text);
        }
      }

      return result;
    });

    // ── Post-extraction validation ──────────────────────────────────────────
    // Final guard: if ANY prompt in ANY use case contains "What's New",
    // the whole batch is a sidebar scrape — discard all use cases.
    if (data.useCases.length > 0) {
      const allPrompts = data.useCases.flatMap(uc => uc.prompts);
      const hasSidebarSignal = allPrompts.some(p =>
        p.includes("What's New") ||
        p === 'Cloud Foundry' ||
        p === 'Finding Apps with Navigational Capability'
      );
      if (hasSidebarSignal) {
        data.useCases = [];
      }
    }

    // If total prompt count is suspiciously high from a single use case,
    // it's almost certainly a sidebar dump — discard.
    if (data.useCases.length === 1 && data.useCases[0].prompts.length > 40) {
      data.useCases = [];
    }

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
  let discarded = 0;

  for (const entry of toScrape) {
    const slug = titleToSlug(entry.title);
    const url = URL_OVERRIDES[slug] || (BASE_URL + slug);

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
    } else if (data.error) {
      discarded++;
      console.log(` ✗ error: ${data.error.substring(0, 60)}`);
    } else {
      console.log(' — no content found');
    }

    // Polite delay between requests
    await new Promise(r => setTimeout(r, 600));
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
      pages_with_errors: discarded,
      source: 'https://help.sap.com/docs/joule/capabilities-guide/',
    },
    pages: results,
  };

  fs.writeFileSync(OUT_FILE, JSON.stringify(output, null, 2));

  console.log('');
  console.log(`✅ Scraped ${scraped} pages`);
  console.log(`   ${withUseCases} pages with use case content`);
  console.log(`   ${scraped - withUseCases - discarded} pages with no content found`);
  if (discarded) console.log(`   ${discarded} pages with errors`);
  console.log(`   💾 Saved to ${OUT_FILE}`);
}

main().catch(console.error);
