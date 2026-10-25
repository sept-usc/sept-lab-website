#!/usr/bin/env node
/* Export square icons from the same original mark used in the page header.
 * Requires Node.js and sharp in the tooling environment; normal site builds
 * use the committed PNGs and have no additional dependency.
 */
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');

const root = path.resolve(__dirname, '..');
const outputs = [
  ['design/favicon-512.png', 512, false],
  ['assets/img/favicon-16.png', 16, false],
  ['assets/img/favicon-32.png', 32, false],
  ['assets/img/icon-192.png', 192, false],
  ['assets/img/apple-touch-icon.png', 180, true],
];

async function main() {
  const site = JSON.parse(await fs.readFile(path.join(root, 'data/site.json'), 'utf8'));
  const source = path.join(root, site.lockup.mark);
  for (const [name, size, white] of outputs) {
    // Keep the original proportions and composition; only add square padding.
    await sharp(source).resize(size, size, {
      fit: 'contain',
      background: { r: 255, g: 255, b: 255, alpha: white ? 1 : 0 },
    }).png().toFile(path.join(root, name));
    console.log(`${name}: ${size} x ${size}`);
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
