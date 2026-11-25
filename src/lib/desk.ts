import { blankCard, type Card } from "@/lib/cards";

export type LoreEntry = { id: string; keys: string; content: string; enabled: boolean };
export type ChatLine = { id: string; role: "user" | "assistant"; text: string };

export type GenerateSettings = {
  prompt: string;
  negative: string;
  promptName: string;
  savedPrompts: { name: string; prompt: string; negative: string }[];
  steps: number;
  cfg: number;
  width: number;
  height: number;
  batch: number;
  seed: string;
  model: string;
  models: string;
  clip: string;
  clipG: string;
  vae: string;
  tile: boolean;
  tileSize: number;
  tileOverlap: number;
  eyes: boolean;
  eyeFile: string;
  eyeDenoise: number;
  eyeConfidence: number;
  eyePrompt: string;
  loras: { path: string; weight: number }[];
  output: string;
};

export type CaptionSettings = {
  engine: "kobold" | "clip" | "joy";
  kind: "character" | "style" | "concept";
  ask: string;
  trigger: string;
  folder: string;
  vision: string;
  visionText: string;
  joy: string;
  mmproj: string;
  copyPictures: boolean;
  skipExisting: boolean;
  files: string;
};

export type Stats = { hp: number; atk: number; def: number; spd: number; note: string };

export type TrainSettings = {
  subject: "character" | "style" | "concept";
  folder: string;
  trigger: string;
  name: string;
  rank: number;
  alpha: number;
  lr: string;
  steps: number;
  resolution: number;
  buckets: boolean;
  checkpoint: boolean;
  cache: boolean;
  noHalf: boolean;
};

export type NovelSettings = {
  seed: string;
  style: string;
  steps: number;
  guidance: number;
  rescale: number;
  uc: number;
  prefix: string;
  negative: string;
  sampler: string;
  schedule: string;
  autoSize: boolean;
  width: number;
  height: number;
  strength: number;
  fidelity: number;
  plate: string;
};

export const novelDefaults: NovelSettings = {
  seed: "-1",
  style: "Anime",
  steps: 25,
  guidance: 6.8,
  rescale: 0,
  uc: 2,
  prefix: "score_9_up, detailed skin, high detail, shiny skin,",
  negative: "artist name, signature, watermark, holding, blurry, jpeg artifacts, username, signature, normal quality, worst quality, large head.",
  sampler: "k_euler_ancestral",
  schedule: "karras",
  autoSize: false,
  width: 1024,
  height: 1024,
  strength: 0.65,
  fidelity: 0.65,
  plate: "",
};

export type Look = {
  dialogue: string;
  nameColor: string;
  messageBox: string;
  boldDialogue: boolean;
  textSize: number;
};

export type Pool = { id: string; name: string; current: number; max: number; color: string };
export type Attr = { id: string; name: string; value: number };
export type OnboardStep = { id: string; title: string; prompt: string; enabled: boolean };
export type Sprite = { id: string; kind: "face" | "body" | "clip"; label: string; note: string };
export type RegexScript = { id: string; find: string; replace: string; enabled: boolean };
export type VersionSnap = { id: string; version: string; at: string; note: string; card?: Card };
export type RefPic = { id: string; name: string; url: string };
export type Lorebook = {
  id: string;
  name: string;
  category: "World" | "Character" | "NPC" | "Spellbook" | "Other";
  description: string;
  global: boolean;
  embedded: boolean;
  entries: LoreEntry[];
};
export type LifeBeat = { id: string; when: string; title: string; body: string };
export type Sampler = {
  id: string;
  name: string;
  temperature: number;
  topP: number;
  topK: number;
  minP: number;
  repPen: number;
  maxTokens: number;
};
export type Convo = { name: string; temperature: number; maxTokens: number; topP: number; instruct: string; stops: string };
export type SpriteLayout = {
  expressionSize: number;
  bodySize: number;
  expressionOpacity: number;
  bodyOpacity: number;
  side: "left" | "right";
};

export type Desk = {
  mode: "characters" | "personas" | "chat" | "lorebooks" | "pictures" | "library" | "life" | "presets" | "novel" | "theme";
  pictureTab: "generate" | "library" | "captions" | "train";
  editorTab: "metadata" | "card" | "onboarding" | "convo" | "lore" | "sprites" | "gallery" | "colors" | "voice" | "stats" | "advanced";
  concept: string;
  fillEmpty: boolean;
  sendRefs: boolean;
  references: RefPic[];
  starredRef: string;
  writerTemp: number;
  writerMax: number;
  linkedBook: string;
  kobold: string;
  koboldKey: string;
  novelToken: string;
  novelModel: string;
  novelSetup: NovelSettings;
  card: Card;
  title: string;
  favorite: boolean;
  personaMode: boolean;
  greetings: string;
  lore: LoreEntry[];
  look: Look;
  voice: string;
  phonetic: string;
  stats: Stats;
  rpg: boolean;
  pools: Pool[];
  attrs: Attr[];
  personaBars: Pool[];
  depthPrompt: string;
  depth: number;
  depthRole: "system" | "user" | "assistant";
  portrait: string;
  gallery: string[];
  library: { id: string; card: Card; title: string; favorite: boolean; portrait: string; concept?: string }[];
  personas: { id: string; card: Card; title: string; concept?: string }[];
  activePersona: string;
  openCardId: string;
  chat: ChatLine[];
  memory: string;
  generate: GenerateSettings;
  captions: CaptionSettings;
  train: TrainSettings;
  status: string;
  characterId: string;
  autoVersion: boolean;
  versions: VersionSnap[];
  imageOverride: boolean;
  imageTags: string;
  onboarding: OnboardStep[];
  convo: Convo;
  sprites: Sprite[];
  spriteKind: "face" | "body" | "clip";
  spriteLayout: SpriteLayout;
  regex: RegexScript[];
  lorebooks: Lorebook[];
  life: LifeBeat[];
  presets: Sampler[];
  activePreset: string;
  picFolder: string;
  picSubs: boolean;
  picList: string;
};

const KEY = "redwright-desk";

export function defaultGenerate(): GenerateSettings {
  return {
    prompt: "",
    negative: "",
    promptName: "",
    savedPrompts: [],
    steps: 20,
    cfg: 7,
    width: 512,
    height: 512,
    batch: 1,
    seed: "",
    model: "",
    models: "",
    clip: "",
    clipG: "",
    vae: "",
    tile: false,
    tileSize: 512,
    tileOverlap: 64,
    eyes: false,
    eyeFile: "",
    eyeDenoise: 0.55,
    eyeConfidence: 0.3,
    eyePrompt: "detailed eyes, sharp pupils, clear iris",
    loras: [{ path: "", weight: 1 }],
    output: "",
  };
}

export function blankDesk(): Desk {
  return {
    mode: "characters",
    pictureTab: "generate",
    editorTab: "card",
    concept: "",
    fillEmpty: false,
    sendRefs: false,
    references: [],
    starredRef: "",
    writerTemp: 0.8,
    writerMax: 16000,
    linkedBook: "",
    kobold: "http://127.0.0.1:5001/v1",
    koboldKey: "",
    novelToken: "",
    novelModel: "nai-diffusion-5-full",
    novelSetup: { ...novelDefaults },
    card: blankCard(),
    title: "",
    favorite: false,
    personaMode: false,
    greetings: "",
    lore: [],
    look: { dialogue: "", nameColor: "#e8b86d", messageBox: "", boldDialogue: true, textSize: 16 },
    voice: "",
    phonetic: "",
    stats: { hp: 100, atk: 10, def: 10, spd: 10, note: "" },
    rpg: true,
    pools: [
      { id: "hp", name: "HP", current: 100, max: 100, color: "#e23d2b" },
      { id: "mp", name: "MP", current: 100, max: 100, color: "#8a9a7b" },
    ],
    attrs: [
      { id: "str", name: "STR", value: 10 },
      { id: "dex", name: "DEX", value: 10 },
      { id: "con", name: "CON", value: 10 },
      { id: "int", name: "INT", value: 10 },
      { id: "wis", name: "WIS", value: 10 },
      { id: "cha", name: "CHA", value: 10 },
    ],
    personaBars: [
      { id: "satiety", name: "Satiety", current: 100, max: 100, color: "#c4a574" },
      { id: "energy", name: "Energy", current: 100, max: 100, color: "#d7c4a3" },
      { id: "hygiene", name: "Hygiene", current: 100, max: 100, color: "#8a9a7b" },
      { id: "mood", name: "Mood", current: 100, max: 100, color: "#e23d2b" },
    ],
    depthPrompt: "",
    depth: 4,
    depthRole: "system",
    portrait: "",
    gallery: [],
    library: [],
    personas: [],
    activePersona: "",
    openCardId: "",
    chat: [],
    memory: "",
    generate: defaultGenerate(),
    captions: {
      engine: "kobold",
      kind: "character",
      ask: "Describe this person for a training caption. Cover face, hair, clothes, pose, and the setting. Use one line of comma-separated phrases.",
      trigger: "",
      folder: "",
      vision: "",
      visionText: "",
      joy: "",
      mmproj: "",
      copyPictures: true,
      skipExisting: true,
      files: "",
    },
    train: {
      subject: "character",
      folder: "",
      trigger: "",
      name: "trained",
      rank: 32,
      alpha: 16,
      lr: "0.0001",
      steps: 400,
      resolution: 512,
      buckets: true,
      checkpoint: true,
      cache: true,
      noHalf: true,
    },
    status: "Ready.",
    characterId: "",
    autoVersion: true,
    versions: [],
    imageOverride: false,
    imageTags: "",
    onboarding: [
      { id: "meet", title: "How you meet", prompt: "Ask how {{user}} and {{char}} meet, then lock it into the scenario.", enabled: true },
      { id: "voice", title: "How they talk", prompt: "Ask for a speech habit and write it into personality.", enabled: true },
      { id: "line", title: "A line they will not cross", prompt: "Ask for one hard boundary and store it in creator notes.", enabled: false },
    ],
    convo: {
      name: "Roleplay",
      temperature: 0.8,
      maxTokens: 420,
      topP: 0.95,
      instruct: "Stay in character. Actions go in asterisks. Do not speak for {{user}}.",
      stops: "",
    },
    sprites: [],
    spriteKind: "face",
    spriteLayout: { expressionSize: 100, bodySize: 100, expressionOpacity: 100, bodyOpacity: 100, side: "left" },
    regex: [],
    lorebooks: [],
    life: [],
    presets: [
      { id: "cardwright", name: "Cardwright", temperature: 0.8, topP: 0.95, topK: 0, minP: 0.05, repPen: 1.1, maxTokens: 2200 },
      { id: "precise", name: "Precise", temperature: 0.4, topP: 0.9, topK: 40, minP: 0.1, repPen: 1.15, maxTokens: 900 },
      { id: "wild", name: "Wild", temperature: 1.15, topP: 0.98, topK: 0, minP: 0.02, repPen: 1.05, maxTokens: 1200 },
    ],
    activePreset: "cardwright",
    picFolder: "",
    picSubs: false,
    picList: "",
  };
}

export function loadDesk(): Desk {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return blankDesk();
    const parsed = JSON.parse(raw) as Partial<Desk>;
    const blank = blankDesk();
    const modes = new Set(["characters", "personas", "chat", "lorebooks", "pictures", "library", "life", "presets", "novel", "theme"]);
    const editors = new Set(["metadata", "card", "onboarding", "convo", "lore", "sprites", "gallery", "colors", "voice", "stats", "advanced"]);
    const pictures = new Set(["generate", "library", "captions", "train"]);
    return {
      ...blank,
      ...parsed,
      mode: modes.has(String(parsed.mode)) ? parsed.mode! : blank.mode,
      editorTab: editors.has(String(parsed.editorTab)) ? parsed.editorTab! : blank.editorTab,
      pictureTab: pictures.has(String(parsed.pictureTab)) ? parsed.pictureTab! : blank.pictureTab,
      card: { ...blankCard(), ...parsed.card },
      generate: { ...defaultGenerate(), ...parsed.generate },
      captions: { ...blank.captions, ...parsed.captions },
      train: { ...blank.train, ...parsed.train },
      look: { ...blank.look, ...parsed.look },
      stats: { ...blank.stats, ...parsed.stats },
      convo: { ...blank.convo, ...parsed.convo },
      novelSetup: { ...blank.novelSetup, ...parsed.novelSetup },
      spriteLayout: { ...blank.spriteLayout, ...parsed.spriteLayout },
      pools: parsed.pools?.length ? parsed.pools : blank.pools,
      attrs: parsed.attrs?.length ? parsed.attrs : blank.attrs,
      personaBars: parsed.personaBars?.length ? parsed.personaBars : blank.personaBars,
      presets: parsed.presets?.length ? parsed.presets : blank.presets,
      onboarding: parsed.onboarding?.length ? parsed.onboarding : blank.onboarding,
      lore: parsed.lore ?? [],
      lorebooks: parsed.lorebooks ?? [],
      sprites: parsed.sprites ?? [],
      regex: parsed.regex ?? [],
      versions: parsed.versions ?? [],
      life: parsed.life ?? [],
      gallery: parsed.gallery ?? [],
      library: parsed.library ?? [],
      personas: parsed.personas ?? [],
      references: parsed.references ?? [],
      chat: parsed.chat ?? [],
    };
  } catch {
    return blankDesk();
  }
}

export function saveDesk(desk: Desk) {
  const references = (desk.references ?? []).filter((item) => item.url.length < 180_000);
  const copy = {
    ...desk,
    portrait: desk.portrait.length > 400_000 ? "" : desk.portrait,
    gallery: desk.gallery,
    references,
  };
  try {
    localStorage.setItem(KEY, JSON.stringify(copy));
  } catch {
    localStorage.setItem(KEY, JSON.stringify({ ...copy, references: [], portrait: "", gallery: [] }));
  }
}
