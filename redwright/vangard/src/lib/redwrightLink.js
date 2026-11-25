/**
 * Copies RedWright libraries into the open Ren'Py project.
 * RedWright publishes redwright-link/bridge.json. This module only writes
 * under game/images/redwright and game/redwright.rpy.
 */
import fs from 'fs/promises';
import os from 'os';
import path from 'path';

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp']);

export function renpySlug(name, used) {
  let text = String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  if (!text || /^[0-9]/.test(text)) text = `item_${text}`.replace(/_+$/g, '');
  text = text.slice(0, 40) || 'item';
  let choice = text;
  let count = 2;
  while (used.has(choice)) {
    choice = `${text.slice(0, 34)}_${count}`;
    count += 1;
  }
  used.add(choice);
  return choice;
}

export function renpyString(text) {
  return `"${String(text || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function pointerPath() {
  if (process.platform === 'win32') {
    const root = process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming');
    return path.join(root, 'RedGen', 'redwright-link.json');
  }
  return path.join(os.homedir(), '.redgen', 'redwright-link.json');
}

async function readJson(file) {
  try {
    const data = JSON.parse(await fs.readFile(file, 'utf-8'));
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

export async function locateBridge(redwrightHome = '') {
  const candidates = [];
  if (redwrightHome) candidates.push(path.join(redwrightHome, 'redwright-link', 'bridge.json'));
  const pointer = await readJson(pointerPath());
  if (pointer?.home) candidates.push(path.join(pointer.home, 'redwright-link', 'bridge.json'));
  if (pointer?.generated || pointer?.cards) return { bridge: pointer, file: pointerPath() };
  for (const file of candidates) {
    const bridge = await readJson(file);
    if (bridge) return { bridge, file };
  }
  return null;
}

async function listImages(dir, subfolders) {
  const found = [];
  async function walk(folder) {
    let entries = [];
    try {
      entries = await fs.readdir(folder, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (!entry.name || entry.name.startsWith('.')) continue;
      const full = path.join(folder, entry.name);
      if (entry.isDirectory()) {
        if (subfolders && entry.name !== 'node_modules') await walk(full);
        continue;
      }
      if (IMAGE_EXT.has(path.extname(entry.name).toLowerCase())) found.push(full);
    }
  }
  if (dir) await walk(dir);
  return found;
}

function safeParts(root, file) {
  const rel = path.relative(root, file);
  if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) return null;
  const parts = rel.split(path.sep).filter((part) => part && part !== '.' && part !== '..');
  if (!parts.length) return null;
  return parts.map((part) => part.replace(/[^A-Za-z0-9._-]+/g, '_'));
}

async function sidecarPrompt(file) {
  const textPath = file.replace(/\.[^.]+$/, '.txt');
  try {
    const text = (await fs.readFile(textPath, 'utf-8')).trim();
    if (text) return text;
  } catch { /* no sidecar */ }
  const jsonPath = file.replace(/\.[^.]+$/, '.json');
  const data = await readJson(jsonPath);
  return String(data?.prompt || data?.summary || '').trim();
}

async function copyGroup(projectRoot, bucket, files, rootForRelative) {
  const copied = [];
  const destRoot = path.join(projectRoot, 'game', 'images', 'redwright', bucket);
  for (const file of files) {
    const parts = safeParts(rootForRelative, file);
    if (!parts) continue;
    const dest = path.join(destRoot, ...parts);
    const relative = path.relative(path.join(projectRoot, 'game'), dest).split(path.sep).join('/');
    if (relative.startsWith('..') || path.isAbsolute(relative)) continue;
    await fs.mkdir(path.dirname(dest), { recursive: true });
    let same = false;
    try {
      const [from, to] = await Promise.all([fs.stat(file), fs.stat(dest)]);
      same = from.size === to.size;
    } catch { /* dest missing */ }
    if (!same) await fs.copyFile(file, dest);
    copied.push({ file, relative, prompt: await sidecarPrompt(file) });
  }
  return copied;
}

export async function importRedwrightResources({ projectRoot, redwrightHome = '' }) {
  if (!projectRoot) return { success: false, error: 'Open a Ren\'Py project first.' };
  const located = await locateBridge(redwrightHome);
  if (!located) {
    return { success: false, error: 'RedWright has not published its libraries yet. Open RedWright once, then click RedWright again.' };
  }
  const bridge = located.bridge;
  const generated = await listImages(bridge.generated || '', Boolean(bridge.generatedSubfolders));
  const novel = await listImages(bridge.novel || '', false);
  const held = await listImages(bridge.looseNovel || '', false);
  const cards = await listImages(bridge.cards || '', false);
  const pictures = [
    ...await copyGroup(projectRoot, 'generated', generated, bridge.generated),
    ...await copyGroup(projectRoot, 'novel', novel, bridge.novel),
    ...await copyGroup(projectRoot, 'novel', held, bridge.looseNovel),
    ...await copyGroup(projectRoot, 'cards', cards, bridge.cards),
  ];
  const used = new Set();
  const lines = [
    '# Generated by RedWright. Click RedWright in Vangard again to refresh.',
    '# Pictures live in game/images/redwright.',
    '',
  ];
  const imageNameByRelative = new Map();
  for (const picture of pictures) {
    const stem = path.basename(picture.relative, path.extname(picture.relative));
    const kind = picture.relative.includes('/cards/') ? 'card' : picture.relative.includes('/novel/') ? 'novel' : 'gen';
    const name = renpySlug(`${kind}_${stem}`, used);
    imageNameByRelative.set(picture.relative, name);
    const note = picture.prompt.replace(/\s+/g, ' ').slice(0, 180).replace(/[^\x20-\x7e]/g, '');
    if (note) lines.push(`# ${note}`);
    lines.push(`image rw_${name} = ${renpyString(picture.relative)}`);
    lines.push('');
  }
  const cardDir = bridge.cards || '';
  let cardDefines = 0;
  if (cardDir) {
    let entries = [];
    try {
      entries = await fs.readdir(cardDir);
    } catch { entries = []; }
    const names = new Set();
    for (const entry of entries.filter((name) => name.endsWith('.json'))) {
      const meta = await readJson(path.join(cardDir, entry));
      if (!meta?.name) continue;
      const slug = renpySlug(String(meta.name), names);
      const stem = path.basename(entry, '.json');
      const imageName = [...imageNameByRelative.entries()].find(([relative]) => relative.endsWith(`/cards/${stem}.png`) || relative.endsWith(`/cards/${stem}.jpg`) || relative.endsWith(`/cards/${stem}.jpeg`) || relative.endsWith(`/cards/${stem}.webp`))?.[1];
      const imageArg = imageName ? `, image=${renpyString(`rw_${imageName}`)}` : '';
      lines.push(`define rw_${slug} = Character(${renpyString(meta.name)}${imageArg})`);
      cardDefines += 1;
    }
    if (cardDefines) lines.push('');
  }
  const script = path.join(projectRoot, 'game', 'redwright.rpy');
  await fs.mkdir(path.dirname(script), { recursive: true });
  await fs.writeFile(script, `${lines.join('\n').replace(/\n{3,}/g, '\n\n')}\n`, 'utf-8');
  const cardCount = cards.length;
  return {
    success: true,
    images: pictures.length,
    cards: cardCount,
    message: `Brought in ${pictures.length} picture${pictures.length === 1 ? '' : 's'} and ${cardDefines} character${cardDefines === 1 ? '' : 's'}. See game/redwright.rpy.`,
  };
}
