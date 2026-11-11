// Copia distribuições fixas do npm para o diretório coletado pelo Django.
// Não modifica dados da obra nem exige serviços externos em runtime.
import { cpSync, existsSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const nodeModules = join(root, 'node_modules');
const target = join(root, 'obras', 'static', 'obras', 'vendor');

const sources = [
  ['apexcharts/dist/apexcharts.min.js', 'apexcharts/apexcharts.min.js'],
  ['three/build/three.module.js', 'three/build/three.module.js'],
  ['three/examples/jsm', 'three/examples/jsm'],
  ['@fortawesome/fontawesome-free/css/all.min.css', 'fontawesome/css/all.min.css'],
  ['@fortawesome/fontawesome-free/webfonts', 'fontawesome/webfonts'],
];

for (const [source, dest] of sources) {
  const origem = join(nodeModules, source);
  const destino = join(target, dest);
  if (!existsSync(origem)) {
    throw new Error(`Dependência ausente: ${source}. Execute npm ci.`);
  }
  mkdirSync(resolve(destino, '..'), { recursive: true });
  cpSync(origem, destino, { recursive: true, force: true });
}

console.log('Arquivos estáticos locais compilados para o Django.');
