#!/usr/bin/env node
/* Export the small tree-and-thinker mark from its editable SVG.
 * Requires Node.js and sharp in the tooling environment; normal site builds
 * use the committed PNGs and have no additional dependency.
 */
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');

const root = path.resolve(__dirname, '..');
const outputs = [
  ['design/favicon-512.png', 512, false],
  ['assets/img/favicon-32.png', 32, false],
  ['assets/img/icon-192.png', 192, false],
  ['assets/img/apple-touch-icon.png', 180, true],
];

async function main() {
  const source = await fs.readFile(path.join(root, 'assets/img/favicon.svg'), 'utf8');
  for (const [name, size, white] of outputs) {
    // Set the vector viewport before rendering; do not enlarge a raster export.
    let svg = source.replace('<svg ', `<svg width="${size}" height="${size}" `);
    if (white) {
      svg = svg.replace(/(<svg[^>]*>)/, '$1<rect width="64" height="64" fill="#fff"/>');
    }
    await sharp(Buffer.from(svg)).png().toFile(path.join(root, name));
    console.log(`${name}: ${size} x ${size}`);
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
