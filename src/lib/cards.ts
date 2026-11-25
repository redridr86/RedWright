export type Card = {
  name: string;
  summary: string;
  description: string;
  personality: string;
  scenario: string;
  first_mes: string;
  mes_example: string;
  creator_notes: string;
  system_prompt: string;
  post_history_instructions: string;
  tags: string[];
  creator: string;
  character_version: string;
  alternate_greetings: string[];
  backstory: string;
  appearance: string;
  talkativeness: number;
  aliases: string;
  long_memory: string;
};

export const FIELDS: { key: keyof Card; label: string; rows: number }[] = [
  { key: "name", label: "Name", rows: 1 },
  { key: "summary", label: "Summary", rows: 2 },
  { key: "description", label: "Description", rows: 4 },
  { key: "personality", label: "Personality", rows: 3 },
  { key: "backstory", label: "Backstory", rows: 3 },
  { key: "appearance", label: "Appearance", rows: 3 },
  { key: "scenario", label: "Scenario", rows: 3 },
  { key: "first_mes", label: "First message", rows: 4 },
  { key: "mes_example", label: "Examples", rows: 4 },
  { key: "creator_notes", label: "Creator notes", rows: 2 },
];

export function blankCard(): Card {
  return {
    name: "",
    summary: "",
    description: "",
    personality: "",
    scenario: "",
    first_mes: "",
    mes_example: "",
    creator_notes: "",
    system_prompt: "",
    post_history_instructions: "",
    tags: [],
    creator: "Cardwright",
    character_version: "1.0",
    alternate_greetings: [],
    backstory: "",
    appearance: "",
    talkativeness: 50,
    aliases: "",
    long_memory: "",
  };
}

export function koboldRoot(base: string): string {
  let text = base.trim().replace(/\/+$/, "");
  if (!text) text = "http://127.0.0.1:5001/v1";
  if (!/^https?:\/\//i.test(text)) text = `http://${text}`;
  if (!/\/v1$/i.test(text)) text += "/v1";
  return text;
}

function asStrings(value: unknown): string[] {
  const list = Array.isArray(value) ? value : typeof value === "string" ? [value] : [];
  return list.filter((item): item is string => typeof item === "string" && item.trim().length > 0).map((item) => item.trim());
}

export function normalizeCard(raw: unknown, persona = false): Card {
  const card = blankCard();
  const root = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  const source =
    root.data && typeof root.data === "object" ? (root.data as Record<string, unknown>) : root;
  const extensions =
    source.extensions && typeof source.extensions === "object"
      ? (source.extensions as Record<string, unknown>)
      : {};
  for (const key of Object.keys(card) as (keyof Card)[]) {
    if (key === "tags" || key === "alternate_greetings" || key === "talkativeness") continue;
    const incoming = source[key] ?? (key === "backstory" || key === "appearance" ? extensions[key] : undefined);
    if (typeof incoming === "string") card[key] = incoming;
  }
  const tags = asStrings(source.tags);
  if (tags.length) card.tags = tags.slice(0, 8);
  const greetings = asStrings(source.alternate_greetings);
  if (greetings.length) card.alternate_greetings = greetings;
  const talk = extensions.talkativeness ?? source.talkativeness;
  if (typeof talk === "number" && Number.isFinite(talk)) card.talkativeness = Math.max(0, Math.min(100, Math.round(talk)));
  if (!card.creator.trim()) card.creator = "Cardwright";
  if (!card.character_version.trim()) card.character_version = "1.0";
  if (persona) {
    card.first_mes = "";
    card.alternate_greetings = [];
  }
  return card;
}

export function toV2(card: Card) {
  return {
    spec: "chara_card_v2",
    spec_version: "2.0",
    data: {
      name: card.name.trim() || "Unnamed",
      summary: card.summary,
      description: card.description,
      personality: card.personality,
      scenario: card.scenario,
      first_mes: card.first_mes,
      mes_example: card.mes_example,
      creator_notes: card.creator_notes,
      system_prompt: card.system_prompt,
      post_history_instructions: card.post_history_instructions,
      tags: card.tags,
      creator: card.creator.trim() || "Cardwright",
      character_version: card.character_version.trim() || "1.0",
      alternate_greetings: card.alternate_greetings.map((item) => item.trim()).filter(Boolean),
      character_book: null,
      extensions: {
        talkativeness: card.talkativeness,
        fav: false,
        backstory: card.backstory,
        appearance: card.appearance,
        aliases: card.aliases,
        long_memory: card.long_memory,
      },
    },
  };
}

const SCHEMA = `JSON keys:
{
  "name": "",
  "summary": "",
  "description": "",
  "personality": "",
  "scenario": "",
  "first_mes": "",
  "mes_example": "",
  "creator_notes": "",
  "backstory": "",
  "appearance": "",
  "tags": [],
  "alternate_greetings": [],
  "talkativeness": 50,
  "system_prompt": "",
  "post_history_instructions": ""
}`;

const CARD_SYSTEM = `You write character cards for Marinara Engine, which reads SillyTavern Character Card V2.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{char}} for the character and {{user}} for the person they meet. Do not invent a name for {{user}}.
Write concrete facts, not adjective piles. first_mes is spoken in character, with actions in asterisks.
mes_example contains two or three exchanges, each block starting with <START>.
summary is one sentence for a library list and is not roleplay prose.
tags is an array of 3 to 6 short labels.
talkativeness is an integer from 0 to 100.
Leave system_prompt and post_history_instructions as empty strings unless the concept demands a hard rule.`;

const PERSONA_SYSTEM = `You write a Marinara persona: the character card that stands for the human in a chat, not the character they talk to.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{user}} for this persona and {{char}} for the other character. Do not invent a name for {{char}}.
Write concrete facts. first_mes must be an empty string. alternate_greetings must be an empty array.
mes_example shows how {{user}} speaks, two short exchanges, each block starting with <START>.
summary is one sentence for a library list.
tags is an array of 3 to 6 short labels.
Leave system_prompt and post_history_instructions as empty strings.`;

function jsonObject(text: string): unknown {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const raw = (fenced?.[1] ?? text).trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start < 0 || end <= start) throw new Error("Could not read the card.");
  return JSON.parse(raw.slice(start, end + 1));
}

async function koboldChat(
  base: string,
  key: string,
  messages: { role: string; content: string }[],
  options?: { temperature?: number; maxTokens?: number; topP?: number },
) {
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" };
  if (key.trim()) headers.Authorization = `Bearer ${key.trim()}`;
  let response: Response;
  try {
    response = await fetch(`${koboldRoot(base)}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: "koboldcpp",
        messages,
        temperature: options?.temperature ?? 0.8,
        max_tokens: options?.maxTokens ?? 2200,
        top_p: options?.topP ?? 0.95,
      }),
    });
  } catch {
    throw new Error("Could not reach KoboldCPP. It has to be running on this computer.");
  }
  if (!response.ok) {
    const detail = (await response.text()).replace(/\s+/g, " ").slice(0, 240);
    throw new Error(detail || `KoboldCPP returned HTTP ${response.status}.`);
  }
  const payload = (await response.json()) as { choices?: { message?: { content?: unknown } }[] };
  const content = payload.choices?.[0]?.message?.content;
  const text = typeof content === "string" ? content : "";
  if (!text.trim()) throw new Error("KoboldCPP returned an empty reply.");
  return text;
}

export async function rewriteField(
  base: string,
  key: string,
  field: string,
  concept: string,
  card?: { [key: string]: unknown },
  options?: { temperature?: number; maxTokens?: number },
) {
  const box = String(card?.[field] ?? "").trim();
  const conceptText = concept.trim();
  const others: Record<string, string> = {};
  if (card) {
    for (const [name, value] of Object.entries(card)) {
      if (name === field || typeof value !== "string" || !value.trim()) continue;
      others[name] = value.trim();
    }
  }
  if (!box && Object.keys(others).length === 0 && conceptText.length < 8) {
    throw new Error("Write a prompt in this box, or fill another field first.");
  }
  const guide = box
    ? `The note in the box is the prompt. Follow it.\n\nPrompt:\n${box}`
    : "The box is empty. Use the other fields as the guidance.";
  const context = [
    Object.keys(others).length ? `Other fields:\n${JSON.stringify(others)}` : "",
    conceptText ? `Concept:\n${conceptText}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  return (
    await koboldChat(
      base,
      key,
      [
        { role: "system", content: "You fill one character-card field. Return only that field's text. No label, no JSON, no markdown." },
        {
          role: "user",
          content: `Write only the ${field} field. Do not write any other field.\n\n${guide}${context ? `\n\n${context}` : ""}`,
        },
      ],
      options,
    )
  ).trim();
}

export async function chatReply(
  base: string,
  key: string,
  system: string,
  history: { role: "user" | "assistant"; text: string }[],
  options?: { temperature?: number; maxTokens?: number; topP?: number },
) {
  return koboldChat(
    base,
    key,
    [{ role: "system", content: system }, ...history.map((line) => ({ role: line.role, content: line.text }))],
    options,
  );
}

export async function writeCard(
  base: string,
  key: string,
  concept: string,
  persona: boolean,
  options?: { temperature?: number; maxTokens?: number },
): Promise<Card> {
  const text = concept.trim();
  if (text.length < 8) {
    throw new Error(persona ? "Describe the persona in a sentence or two." : "Describe the character in a sentence or two.");
  }
  const system = persona ? PERSONA_SYSTEM : CARD_SYSTEM;
  const user =
    (persona ? "Write a persona from this concept:\n" : "Write a full character card from this concept:\n") +
    text +
    "\n\n" +
    SCHEMA;
  const messages = [
    { role: "system", content: system },
    { role: "user", content: user },
  ];
  let reply = await koboldChat(base, key, messages, options);
  try {
    return normalizeCard(jsonObject(reply), persona);
  } catch {
    messages.push({ role: "assistant", content: reply });
    messages.push({ role: "user", content: "That was not valid JSON. Reply again with only the JSON object, no fences." });
    reply = await koboldChat(base, key, messages, options);
    return normalizeCard(jsonObject(reply), persona);
  }
}

export function picturePrompt(card: Card): string {
  const tags: string[] = [];
  for (const part of [card.appearance, card.name, card.scenario]) {
    for (const piece of part.split(/[,;\n]+/)) {
      const clean = piece.trim();
      if (clean && !tags.includes(clean)) tags.push(clean);
    }
  }
  return tags.join(", ");
}

export function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "character";
}

function crcTable() {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
}

const CRC = crcTable();

function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (const byte of bytes) c = CRC[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type: string, data: Uint8Array): Uint8Array {
  const out = new Uint8Array(12 + data.length);
  const view = new DataView(out.buffer);
  view.setUint32(0, data.length);
  out.set(new TextEncoder().encode(type), 4);
  out.set(data, 8);
  const signed = new Uint8Array(4 + data.length);
  signed.set(out.subarray(4, 8), 0);
  signed.set(data, 4);
  view.setUint32(8 + data.length, crc32(signed));
  return out;
}

export async function packPng(card: Card, portrait: Blob | null): Promise<Blob> {
  const source = portrait ?? (await textPlate(card));
  const bytes = new Uint8Array(await source.arrayBuffer());
  if (bytes.length < 8 || bytes[0] !== 0x89) throw new Error("The portrait has to be a PNG.");
  const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(toV2(card)))));
  const text = new Uint8Array(encoded.length + 6);
  text.set(new TextEncoder().encode("chara"), 0);
  text.set(new TextEncoder().encode(encoded), 6);
  const extra = chunk("tEXt", text);
  let iend = -1;
  let offset = 8;
  while (offset + 8 <= bytes.length) {
    const length = new DataView(bytes.buffer, bytes.byteOffset + offset, 4).getUint32(0);
    const type = String.fromCharCode(bytes[offset + 4], bytes[offset + 5], bytes[offset + 6], bytes[offset + 7]);
    if (type === "IEND") {
      iend = offset;
      break;
    }
    offset += 12 + length;
  }
  if (iend < 0) throw new Error("That PNG is missing its end.");
  const merged = new Uint8Array(bytes.length + extra.length);
  merged.set(bytes.subarray(0, iend), 0);
  merged.set(extra, iend);
  merged.set(bytes.subarray(iend), iend + extra.length);
  return new Blob([merged], { type: "image/png" });
}

async function textPlate(card: Card): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 832;
  canvas.height = 1216;
  const pen = canvas.getContext("2d");
  if (!pen) throw new Error("Could not draw the card plate.");
  pen.fillStyle = "#1c1a17";
  pen.fillRect(0, 0, 832, 1216);
  pen.strokeStyle = "#e23d2b";
  pen.lineWidth = 3;
  pen.strokeRect(36, 36, 760, 1144);
  pen.fillStyle = "#f4efe6";
  pen.font = "48px Palatino, Georgia, serif";
  pen.fillText((card.name.trim() || "Unnamed").slice(0, 28), 64, 120);
  pen.fillStyle = "#a39b90";
  pen.font = "22px Segoe UI, sans-serif";
  const summary = card.summary.trim() || "No summary yet.";
  let y = 180;
  for (const line of wrap(summary, 42)) {
    pen.fillText(line, 64, y);
    y += 30;
  }
  pen.fillStyle = "#e23d2b";
  pen.font = "18px Segoe UI, sans-serif";
  pen.fillText("RedWright  ·  text plate, not a portrait", 64, 1140);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Could not pack the PNG card.");
  return blob;
}

function wrap(text: string, width: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const trial = line ? `${line} ${word}` : word;
    if (trial.length > width) {
      if (line) lines.push(line);
      line = word;
    } else line = trial;
  }
  if (line) lines.push(line);
  return lines.slice(0, 28);
}

export function download(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
