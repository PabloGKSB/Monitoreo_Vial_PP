import {build} from 'esbuild';
import {copyFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

process.chdir(fileURLToPath(new URL('.', import.meta.url)));
await mkdir('dist/assets', {recursive: true});
await build({entryPoints: ['client.js'], outdir: 'dist/assets', bundle: true,
  minify: true, format: 'esm', target: 'es2022', loader: {'.png': 'dataurl'}});
await copyFile('index.html', 'dist/index.html');
await copyFile('styles.css', 'dist/assets/styles.css');
