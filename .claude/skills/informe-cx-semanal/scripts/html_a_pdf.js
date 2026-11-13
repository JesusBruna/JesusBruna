// Uso: node html_a_pdf.js <archivo.html> [salida.pdf] [captura.png]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const src = path.resolve(process.argv[2]);
  const out = process.argv[3] || src.replace(/\.html$/, '.pdf');
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1100, height: 900 }, colorScheme: 'light' });
  await p.goto('file://' + src);
  await p.pdf({ path: out, format: 'A4', landscape: true, printBackground: true, margin: { top: '12mm', bottom: '12mm', left: '10mm', right: '10mm' }, scale: 0.72 });
  if (process.argv[4]) await p.screenshot({ path: process.argv[4], fullPage: true });
  await b.close();
  console.log('OK ->', out);
})();
