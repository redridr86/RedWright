import { i as __toESM } from "../_runtime.mjs";
import { K as require_react, b as require_jsx_runtime } from "../_libs/@tanstack/react-router+[...].mjs";
import { a as Shuffle, c as ImagePlus, i as Star, l as Download, o as RefreshCw, r as Trash2, s as Plus, t as Upload, u as Copy } from "../_libs/lucide-react.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-B1MkRp4Q.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function blankCard() {
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
		long_memory: ""
	};
}
function koboldRoot(base) {
	let text = base.trim().replace(/\/+$/, "");
	if (!text) text = "http://127.0.0.1:5001/v1";
	if (!/^https?:\/\//i.test(text)) text = `http://${text}`;
	if (!/\/v1$/i.test(text)) text += "/v1";
	return text;
}
function asStrings(value) {
	return (Array.isArray(value) ? value : typeof value === "string" ? [value] : []).filter((item) => typeof item === "string" && item.trim().length > 0).map((item) => item.trim());
}
function normalizeCard(raw, persona = false) {
	const card = blankCard();
	const root = raw && typeof raw === "object" ? raw : {};
	const source = root.data && typeof root.data === "object" ? root.data : root;
	const extensions = source.extensions && typeof source.extensions === "object" ? source.extensions : {};
	for (const key of Object.keys(card)) {
		if (key === "tags" || key === "alternate_greetings" || key === "talkativeness") continue;
		const incoming = source[key] ?? (key === "backstory" || key === "appearance" ? extensions[key] : void 0);
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
function toV2(card) {
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
				long_memory: card.long_memory
			}
		}
	};
}
var SCHEMA = `JSON keys:
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
var CARD_SYSTEM = `You write character cards for Marinara Engine, which reads SillyTavern Character Card V2.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{char}} for the character and {{user}} for the person they meet. Do not invent a name for {{user}}.
Write concrete facts, not adjective piles. first_mes is spoken in character, with actions in asterisks.
mes_example contains two or three exchanges, each block starting with <START>.
summary is one sentence for a library list and is not roleplay prose.
tags is an array of 3 to 6 short labels.
talkativeness is an integer from 0 to 100.
Leave system_prompt and post_history_instructions as empty strings unless the concept demands a hard rule.`;
var PERSONA_SYSTEM = `You write a Marinara persona: the character card that stands for the human in a chat, not the character they talk to.
Return one JSON object and nothing else. No markdown fences. No commentary.
Use {{user}} for this persona and {{char}} for the other character. Do not invent a name for {{char}}.
Write concrete facts. first_mes must be an empty string. alternate_greetings must be an empty array.
mes_example shows how {{user}} speaks, two short exchanges, each block starting with <START>.
summary is one sentence for a library list.
tags is an array of 3 to 6 short labels.
Leave system_prompt and post_history_instructions as empty strings.`;
function jsonObject(text) {
	const raw = (text.match(/```(?:json)?\s*([\s\S]*?)```/i)?.[1] ?? text).trim();
	const start = raw.indexOf("{");
	const end = raw.lastIndexOf("}");
	if (start < 0 || end <= start) throw new Error("Could not read the card.");
	return JSON.parse(raw.slice(start, end + 1));
}
async function koboldChat(base, key, messages, options) {
	const headers = {
		"Content-Type": "application/json",
		Accept: "application/json"
	};
	if (key.trim()) headers.Authorization = `Bearer ${key.trim()}`;
	let response;
	try {
		response = await fetch(`${koboldRoot(base)}/chat/completions`, {
			method: "POST",
			headers,
			body: JSON.stringify({
				model: "koboldcpp",
				messages,
				temperature: options?.temperature ?? .8,
				max_tokens: options?.maxTokens ?? 2200,
				top_p: options?.topP ?? .95
			})
		});
	} catch {
		throw new Error("Could not reach KoboldCPP. It has to be running on this computer.");
	}
	if (!response.ok) {
		const detail = (await response.text()).replace(/\s+/g, " ").slice(0, 240);
		throw new Error(detail || `KoboldCPP returned HTTP ${response.status}.`);
	}
	const content = (await response.json()).choices?.[0]?.message?.content;
	const text = typeof content === "string" ? content : "";
	if (!text.trim()) throw new Error("KoboldCPP returned an empty reply.");
	return text;
}
async function rewriteField(base, key, field, concept, options) {
	const prompt = concept.trim();
	if (prompt.length < 8) throw new Error("Put the prompt in Concept first.");
	return (await koboldChat(base, key, [{
		role: "system",
		content: "You fill one character-card field from the concept. Return only that field's text. No label, no JSON, no markdown."
	}, {
		role: "user",
		content: `Write only the ${field} field from this concept. Do not write any other field.\n\nConcept:\n${prompt}`
	}], options)).trim();
}
async function chatReply(base, key, system, history, options) {
	return koboldChat(base, key, [{
		role: "system",
		content: system
	}, ...history.map((line) => ({
		role: line.role,
		content: line.text
	}))], options);
}
async function writeCard(base, key, concept, persona, options) {
	const text = concept.trim();
	if (text.length < 8) throw new Error(persona ? "Describe the persona in a sentence or two." : "Describe the character in a sentence or two.");
	const system = persona ? PERSONA_SYSTEM : CARD_SYSTEM;
	const user = (persona ? "Write a persona from this concept:\n" : "Write a full character card from this concept:\n") + text + "\n\n" + SCHEMA;
	const messages = [{
		role: "system",
		content: system
	}, {
		role: "user",
		content: user
	}];
	let reply = await koboldChat(base, key, messages, options);
	try {
		return normalizeCard(jsonObject(reply), persona);
	} catch {
		messages.push({
			role: "assistant",
			content: reply
		});
		messages.push({
			role: "user",
			content: "That was not valid JSON. Reply again with only the JSON object, no fences."
		});
		reply = await koboldChat(base, key, messages, options);
		return normalizeCard(jsonObject(reply), persona);
	}
}
function picturePrompt(card) {
	const tags = [];
	for (const part of [
		card.appearance,
		card.name,
		card.scenario
	]) for (const piece of part.split(/[,;\n]+/)) {
		const clean = piece.trim();
		if (clean && !tags.includes(clean)) tags.push(clean);
	}
	return tags.join(", ");
}
function slug(name) {
	return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "character";
}
function crcTable() {
	const table = /* @__PURE__ */ new Uint32Array(256);
	for (let n = 0; n < 256; n += 1) {
		let c = n;
		for (let k = 0; k < 8; k += 1) c = c & 1 ? 3988292384 ^ c >>> 1 : c >>> 1;
		table[n] = c >>> 0;
	}
	return table;
}
var CRC = crcTable();
function crc32(bytes) {
	let c = 4294967295;
	for (const byte of bytes) c = CRC[(c ^ byte) & 255] ^ c >>> 8;
	return (c ^ 4294967295) >>> 0;
}
function chunk(type, data) {
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
async function packPng(card, portrait) {
	const source = portrait ?? await textPlate(card);
	const bytes = new Uint8Array(await source.arrayBuffer());
	if (bytes.length < 8 || bytes[0] !== 137) throw new Error("The portrait has to be a PNG.");
	const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(toV2(card)))));
	const text = new Uint8Array(encoded.length + 6);
	text.set(new TextEncoder().encode("chara"), 0);
	text.set(new TextEncoder().encode(encoded), 6);
	const extra = chunk("tEXt", text);
	let iend = -1;
	let offset = 8;
	while (offset + 8 <= bytes.length) {
		const length = new DataView(bytes.buffer, bytes.byteOffset + offset, 4).getUint32(0);
		if (String.fromCharCode(bytes[offset + 4], bytes[offset + 5], bytes[offset + 6], bytes[offset + 7]) === "IEND") {
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
async function textPlate(card) {
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
	const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
	if (!blob) throw new Error("Could not pack the PNG card.");
	return blob;
}
function wrap(text, width) {
	const lines = [];
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
function download(name, blob) {
	const url = URL.createObjectURL(blob);
	const link = document.createElement("a");
	link.href = url;
	link.download = name;
	link.click();
	URL.revokeObjectURL(url);
}
var novelDefaults = {
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
	strength: .65,
	fidelity: .65,
	plate: ""
};
var KEY$1 = "redwright-desk";
function defaultGenerate() {
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
		eyeDenoise: .55,
		eyeConfidence: .3,
		eyePrompt: "detailed eyes, sharp pupils, clear iris",
		loras: [{
			path: "",
			weight: 1
		}],
		output: ""
	};
}
function blankDesk() {
	return {
		mode: "characters",
		pictureTab: "generate",
		editorTab: "card",
		concept: "",
		fillEmpty: false,
		sendRefs: false,
		references: [],
		starredRef: "",
		writerTemp: .8,
		writerMax: 16e3,
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
		look: {
			dialogue: "",
			nameColor: "#e8b86d",
			messageBox: "",
			boldDialogue: true,
			textSize: 16
		},
		voice: "",
		phonetic: "",
		stats: {
			hp: 100,
			atk: 10,
			def: 10,
			spd: 10,
			note: ""
		},
		rpg: true,
		pools: [{
			id: "hp",
			name: "HP",
			current: 100,
			max: 100,
			color: "#e23d2b"
		}, {
			id: "mp",
			name: "MP",
			current: 100,
			max: 100,
			color: "#8a9a7b"
		}],
		attrs: [
			{
				id: "str",
				name: "STR",
				value: 10
			},
			{
				id: "dex",
				name: "DEX",
				value: 10
			},
			{
				id: "con",
				name: "CON",
				value: 10
			},
			{
				id: "int",
				name: "INT",
				value: 10
			},
			{
				id: "wis",
				name: "WIS",
				value: 10
			},
			{
				id: "cha",
				name: "CHA",
				value: 10
			}
		],
		personaBars: [
			{
				id: "satiety",
				name: "Satiety",
				current: 100,
				max: 100,
				color: "#c4a574"
			},
			{
				id: "energy",
				name: "Energy",
				current: 100,
				max: 100,
				color: "#d7c4a3"
			},
			{
				id: "hygiene",
				name: "Hygiene",
				current: 100,
				max: 100,
				color: "#8a9a7b"
			},
			{
				id: "mood",
				name: "Mood",
				current: 100,
				max: 100,
				color: "#e23d2b"
			}
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
			files: ""
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
			noHalf: true
		},
		status: "Ready.",
		characterId: "",
		autoVersion: true,
		versions: [],
		imageOverride: false,
		imageTags: "",
		onboarding: [
			{
				id: "meet",
				title: "How you meet",
				prompt: "Ask how {{user}} and {{char}} meet, then lock it into the scenario.",
				enabled: true
			},
			{
				id: "voice",
				title: "How they talk",
				prompt: "Ask for a speech habit and write it into personality.",
				enabled: true
			},
			{
				id: "line",
				title: "A line they will not cross",
				prompt: "Ask for one hard boundary and store it in creator notes.",
				enabled: false
			}
		],
		convo: {
			name: "Roleplay",
			temperature: .8,
			maxTokens: 420,
			topP: .95,
			instruct: "Stay in character. Actions go in asterisks. Do not speak for {{user}}.",
			stops: ""
		},
		sprites: [],
		spriteKind: "face",
		spriteLayout: {
			expressionSize: 100,
			bodySize: 100,
			expressionOpacity: 100,
			bodyOpacity: 100,
			side: "left"
		},
		regex: [],
		lorebooks: [],
		life: [],
		presets: [
			{
				id: "cardwright",
				name: "Cardwright",
				temperature: .8,
				topP: .95,
				topK: 0,
				minP: .05,
				repPen: 1.1,
				maxTokens: 2200
			},
			{
				id: "precise",
				name: "Precise",
				temperature: .4,
				topP: .9,
				topK: 40,
				minP: .1,
				repPen: 1.15,
				maxTokens: 900
			},
			{
				id: "wild",
				name: "Wild",
				temperature: 1.15,
				topP: .98,
				topK: 0,
				minP: .02,
				repPen: 1.05,
				maxTokens: 1200
			}
		],
		activePreset: "cardwright",
		picFolder: "",
		picSubs: false,
		picList: ""
	};
}
function loadDesk() {
	try {
		const raw = localStorage.getItem(KEY$1);
		if (!raw) return blankDesk();
		const parsed = JSON.parse(raw);
		const blank = blankDesk();
		const modes = /* @__PURE__ */ new Set([
			"characters",
			"personas",
			"chat",
			"lorebooks",
			"pictures",
			"library",
			"life",
			"presets",
			"novel",
			"theme"
		]);
		const editors = /* @__PURE__ */ new Set([
			"metadata",
			"card",
			"onboarding",
			"convo",
			"lore",
			"sprites",
			"gallery",
			"colors",
			"voice",
			"stats",
			"advanced"
		]);
		const pictures = /* @__PURE__ */ new Set([
			"generate",
			"library",
			"captions",
			"train"
		]);
		return {
			...blank,
			...parsed,
			mode: modes.has(String(parsed.mode)) ? parsed.mode : blank.mode,
			editorTab: editors.has(String(parsed.editorTab)) ? parsed.editorTab : blank.editorTab,
			pictureTab: pictures.has(String(parsed.pictureTab)) ? parsed.pictureTab : blank.pictureTab,
			card: {
				...blankCard(),
				...parsed.card
			},
			generate: {
				...defaultGenerate(),
				...parsed.generate
			},
			captions: {
				...blank.captions,
				...parsed.captions
			},
			train: {
				...blank.train,
				...parsed.train
			},
			look: {
				...blank.look,
				...parsed.look
			},
			stats: {
				...blank.stats,
				...parsed.stats
			},
			convo: {
				...blank.convo,
				...parsed.convo
			},
			novelSetup: {
				...blank.novelSetup,
				...parsed.novelSetup
			},
			spriteLayout: {
				...blank.spriteLayout,
				...parsed.spriteLayout
			},
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
			chat: parsed.chat ?? []
		};
	} catch {
		return blankDesk();
	}
}
function saveDesk(desk) {
	const references = (desk.references ?? []).filter((item) => item.url.length < 18e4).slice(0, 24);
	const copy = {
		...desk,
		portrait: desk.portrait.length > 4e5 ? "" : desk.portrait,
		gallery: desk.gallery.slice(0, 8),
		references
	};
	try {
		localStorage.setItem(KEY$1, JSON.stringify(copy));
	} catch {
		localStorage.setItem(KEY$1, JSON.stringify({
			...copy,
			references: [],
			portrait: "",
			gallery: []
		}));
	}
}
function Onboarding({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "Questions asked the first time someone opens a chat with this card. They are not sent on later turns."
		}),
		desk.onboarding.map((step) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-3 rounded-md border border-[var(--line)] p-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Step title", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: step.title,
						onChange: (event) => patch({ onboarding: desk.onboarding.map((item) => item.id === step.id ? {
							...item,
							title: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["What to ask", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
						value: step.prompt,
						onChange: (event) => patch({ onboarding: desk.onboarding.map((item) => item.id === step.id ? {
							...item,
							prompt: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "mt-2 flex min-h-11 items-center gap-2 text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "checkbox",
						checked: step.enabled,
						onChange: (event) => patch({ onboarding: desk.onboarding.map((item) => item.id === step.id ? {
							...item,
							enabled: event.target.checked
						} : item) })
					}), "Ask this step"]
				})
			]
		}, step.id)),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => patch({ onboarding: [...desk.onboarding, {
				id: crypto.randomUUID(),
				title: "New step",
				prompt: "",
				enabled: true
			}] }),
			children: "Add step"
		})
	] });
}
function Convo({ desk, patch }) {
	const convo = desk.convo;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "The conversation profile used when Chat sends a turn to KoboldCPP."
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Profile name", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: convo.name,
				onChange: (event) => patch({ convo: {
					...convo,
					name: event.target.value
				} })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Temperature", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "number",
						step: "0.05",
						value: convo.temperature,
						onChange: (event) => patch({ convo: {
							...convo,
							temperature: Number(event.target.value)
						} })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Max tokens", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "number",
						value: convo.maxTokens,
						onChange: (event) => patch({ convo: {
							...convo,
							maxTokens: Number(event.target.value)
						} })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Top P", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "number",
						step: "0.01",
						value: convo.topP,
						onChange: (event) => patch({ convo: {
							...convo,
							topP: Number(event.target.value)
						} })
					})]
				})
			]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Instruct", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: convo.instruct,
				onChange: (event) => patch({ convo: {
					...convo,
					instruct: event.target.value
				} })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Stop sequences, one per line", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: convo.stops,
				onChange: (event) => patch({ convo: {
					...convo,
					stops: event.target.value
				} })
			})]
		})
	] });
}
function Sprites({ desk, patch }) {
	const kinds = [
		["face", "Facial expressions"],
		["body", "Full-body"],
		["clip", "Clips"]
	];
	const layout = desk.spriteLayout;
	const visible = desk.sprites.filter((sprite) => sprite.kind === desk.spriteKind);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-3 flex flex-wrap gap-2",
			children: kinds.map(([id, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				onClick: () => patch({ spriteKind: id }),
				className: `min-h-11 rounded-md px-3 text-sm ${desk.spriteKind === id ? "bg-[var(--red)] font-semibold text-white" : "border border-[var(--line)]"}`,
				children: label
			}, id))
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-3 text-sm text-[var(--muted)]",
			children: "Names the pose or mood. The Windows app and NovelAI can paint the file later. Transparent PNG works best for full-body."
		}),
		visible.map((sprite) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-3 grid gap-2 rounded-md border border-[var(--line)] p-3 sm:grid-cols-[1fr_1fr_auto]",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field mt-0",
					children: ["Label", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: sprite.label,
						onChange: (event) => patch({ sprites: desk.sprites.map((item) => item.id === sprite.id ? {
							...item,
							label: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field mt-0",
					children: ["File or note", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: sprite.note,
						onChange: (event) => patch({ sprites: desk.sprites.map((item) => item.id === sprite.id ? {
							...item,
							note: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					className: "min-h-11 self-end rounded-md border border-[var(--line)] px-3 text-sm",
					onClick: () => patch({ sprites: desk.sprites.filter((item) => item.id !== sprite.id) }),
					children: "Remove"
				})
			]
		}, sprite.id)),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => patch({ sprites: [...desk.sprites, {
				id: crypto.randomUUID(),
				kind: desk.spriteKind,
				label: desk.spriteKind === "face" ? "neutral" : "idle",
				note: ""
			}] }),
			children: "Add sprite"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "display mt-6 text-xl",
			children: "Layout"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Default side", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
				className: "box",
				value: layout.side,
				onChange: (event) => patch({ spriteLayout: {
					...layout,
					side: event.target.value
				} }),
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
					value: "left",
					children: "Left"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
					value: "right",
					children: "Right"
				})]
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [
				["expressionSize", "Expression size"],
				["bodySize", "Full-body size"],
				["expressionOpacity", "Expression opacity"],
				["bodyOpacity", "Full-body opacity"]
			].map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: [
					label,
					" ",
					layout[key],
					"%",
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "range",
						min: key.endsWith("Size") ? 5 : 0,
						max: key.endsWith("Size") ? 200 : 100,
						value: layout[key],
						onChange: (event) => patch({ spriteLayout: {
							...layout,
							[key]: Number(event.target.value)
						} })
					})
				]
			}, key))
		})
	] });
}
function Lorebooks({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: "Lorebooks"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-[var(--muted)]",
				children: "Link a book to the open card, or mark it global so every chat can scan it."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "mt-3 min-h-11 rounded-md bg-[var(--red)] px-3 text-sm font-semibold text-white",
				onClick: () => patch({ lorebooks: [{
					id: crypto.randomUUID(),
					name: "New lorebook",
					category: "Character",
					description: "",
					global: false,
					embedded: false,
					entries: []
				}, ...desk.lorebooks] }),
				children: "New lorebook"
			}),
			desk.lorebooks.map((book) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
				className: "mt-4 rounded-md border border-[var(--line)] p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-3 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "field mt-0",
							children: ["Name", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								value: book.name,
								onChange: (event) => updateBook(desk, patch, book.id, { name: event.target.value })
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "field mt-0",
							children: ["Category", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
								className: "box",
								value: book.category,
								onChange: (event) => updateBook(desk, patch, book.id, { category: event.target.value }),
								children: [
									"World",
									"Character",
									"NPC",
									"Spellbook",
									"Other"
								].map((category) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: category }, category))
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["Description", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
							value: book.description,
							onChange: (event) => updateBook(desk, patch, book.id, { description: event.target.value })
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "mt-2 flex flex-wrap gap-3 text-sm",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "flex min-h-11 items-center gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "checkbox",
									checked: book.global,
									onChange: (event) => updateBook(desk, patch, book.id, { global: event.target.checked })
								}), "Global"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "min-h-11 rounded-md border border-[var(--line)] px-3",
								onClick: () => addEntry(desk, patch, book.id),
								children: "Add entry"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "min-h-11 rounded-md border border-[var(--line)] px-3",
								onClick: () => patch({
									lore: [...desk.lore, ...book.entries.map((entry) => ({
										...entry,
										id: crypto.randomUUID()
									}))],
									lorebooks: desk.lorebooks.map((item) => item.id === book.id ? {
										...item,
										embedded: true
									} : item),
									status: "Embedded into the open card."
								}),
								children: book.embedded ? "Embedded" : "Embed into card"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "min-h-11 px-3 text-[var(--muted)]",
								onClick: () => patch({ lorebooks: desk.lorebooks.filter((item) => item.id !== book.id) }),
								children: "Delete"
							})
						]
					}),
					book.entries.map((entry) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EntryRow, {
						entry,
						onChange: (next) => updateEntry(desk, patch, book.id, next)
					}, entry.id))
				]
			}, book.id)),
			desk.lorebooks.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-4 text-sm text-[var(--muted)]",
				children: "No lorebooks yet."
			}) : null
		]
	});
}
function updateBook(desk, patch, id, partial) {
	patch({ lorebooks: desk.lorebooks.map((book) => book.id === id ? {
		...book,
		...partial
	} : book) });
}
function addEntry(desk, patch, id) {
	patch({ lorebooks: desk.lorebooks.map((book) => book.id === id ? {
		...book,
		entries: [...book.entries, {
			id: crypto.randomUUID(),
			keys: "",
			content: "",
			enabled: true
		}]
	} : book) });
}
function updateEntry(desk, patch, bookId, entry) {
	patch({ lorebooks: desk.lorebooks.map((book) => book.id === bookId ? {
		...book,
		entries: book.entries.map((item) => item.id === entry.id ? entry : item)
	} : book) });
}
function EntryRow({ entry, onChange }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-3 grid gap-2 sm:grid-cols-2",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field mt-0",
			children: ["Keys", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: entry.keys,
				onChange: (event) => onChange({
					...entry,
					keys: event.target.value
				})
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field mt-0",
			children: ["Content", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: entry.content,
				onChange: (event) => onChange({
					...entry,
					content: event.target.value
				})
			})]
		})]
	});
}
function Life({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: "Life"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-[var(--muted)]",
				children: "A timeline that travels with the card. Pinned beats are copied into long memory when you export."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => patch({ life: [{
					id: crypto.randomUUID(),
					when: "",
					title: "",
					body: ""
				}, ...desk.life] }),
				children: "Add beat"
			}),
			desk.life.map((beat) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-3 rounded-md border border-[var(--line)] p-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "grid gap-3 sm:grid-cols-2",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "field mt-0",
							children: ["When", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								value: beat.when,
								onChange: (event) => patch({ life: desk.life.map((item) => item.id === beat.id ? {
									...item,
									when: event.target.value
								} : item) })
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "field mt-0",
							children: ["Title", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								value: beat.title,
								onChange: (event) => patch({ life: desk.life.map((item) => item.id === beat.id ? {
									...item,
									title: event.target.value
								} : item) })
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["What happened", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
							value: beat.body,
							onChange: (event) => patch({ life: desk.life.map((item) => item.id === beat.id ? {
								...item,
								body: event.target.value
							} : item) })
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "mt-2 min-h-11 text-sm text-[var(--muted)]",
						onClick: () => patch({ life: desk.life.filter((item) => item.id !== beat.id) }),
						children: "Remove"
					})
				]
			}, beat.id))
		]
	});
}
function Presets({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: "Presets"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-[var(--muted)]",
				children: "Sampler presets for KoboldCPP writing and chat. The active one is what Write card and Chat use."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-3 grid gap-3 sm:grid-cols-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field mt-0",
						children: ["Kobold address", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							value: desk.kobold,
							onChange: (event) => patch({ kobold: event.target.value })
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field mt-0",
						children: ["API key", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							type: "password",
							value: desk.koboldKey,
							onChange: (event) => patch({ koboldKey: event.target.value })
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["NovelAI token", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							type: "password",
							value: desk.novelToken,
							onChange: (event) => patch({ novelToken: event.target.value })
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["NovelAI model", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							value: desk.novelModel,
							onChange: (event) => patch({ novelModel: event.target.value })
						})]
					})
				]
			}),
			desk.presets.map((preset) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
				className: `mt-4 rounded-md border p-3 ${desk.activePreset === preset.id ? "border-[var(--red)]" : "border-[var(--line)]"}`,
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-wrap items-center justify-between gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field mt-0 min-w-40 flex-1",
						children: ["Name", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							value: preset.name,
							onChange: (event) => updatePreset(desk, patch, preset.id, { name: event.target.value })
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "min-h-11 rounded-md bg-[var(--red)] px-3 text-sm font-semibold text-white",
						onClick: () => patch({ activePreset: preset.id }),
						children: desk.activePreset === preset.id ? "Active" : "Use"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-3 sm:grid-cols-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Temperature",
							value: preset.temperature,
							step: "0.05",
							onChange: (temperature) => updatePreset(desk, patch, preset.id, { temperature })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Top P",
							value: preset.topP,
							step: "0.01",
							onChange: (topP) => updatePreset(desk, patch, preset.id, { topP })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Top K",
							value: preset.topK,
							onChange: (topK) => updatePreset(desk, patch, preset.id, { topK })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Min P",
							value: preset.minP,
							step: "0.01",
							onChange: (minP) => updatePreset(desk, patch, preset.id, { minP })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Repetition penalty",
							value: preset.repPen,
							step: "0.01",
							onChange: (repPen) => updatePreset(desk, patch, preset.id, { repPen })
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
							label: "Max tokens",
							value: preset.maxTokens,
							onChange: (maxTokens) => updatePreset(desk, patch, preset.id, { maxTokens })
						})
					]
				})]
			}, preset.id)),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => patch({ presets: [...desk.presets, {
					id: crypto.randomUUID(),
					name: "Custom",
					temperature: .8,
					topP: .95,
					topK: 0,
					minP: .05,
					repPen: 1.1,
					maxTokens: 800
				}] }),
				children: "New preset"
			})
		]
	});
}
function updatePreset(desk, patch, id, partial) {
	patch({ presets: desk.presets.map((preset) => preset.id === id ? {
		...preset,
		...partial
	} : preset) });
}
function Num$1({ label, value, onChange, step }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "field",
		children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			type: "number",
			step,
			value,
			onChange: (event) => onChange(Number(event.target.value))
		})]
	});
}
function PictureLibrary({ desk, patch }) {
	const names = desk.picList.split("\n").map((line) => line.trim()).filter(Boolean);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "display text-2xl",
			children: "Picture library"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "The folder RedGen scans on your PC. Subfolders stay optional, same as the desktop library tab."
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Folder", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: desk.picFolder,
				onChange: (event) => patch({ picFolder: event.target.value }),
				placeholder: "C:\\\\Pictures\\\\RedWright"
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: desk.picSubs,
				onChange: (event) => patch({ picSubs: event.target.checked })
			}), "Include subfolders"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Picture names, one per line", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.picList,
				onChange: (event) => patch({ picList: event.target.value }),
				placeholder: "seed-12.png"
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-2 text-sm text-[var(--muted)]",
			children: names.length ? `${names.length} pictures listed.` : "No pictures listed yet."
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
			className: "mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4",
			children: names.slice(0, 24).map((name) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
				className: "truncate rounded-md border border-[var(--line)] bg-[var(--surface)] px-2 py-3 text-xs text-[var(--muted)]",
				children: name
			}, name))
		})
	] });
}
var NOVEL_MODELS = [
	["V5 Full", "nai-diffusion-5-full"],
	["V5 Curated", "nai-diffusion-5-curated"],
	["V4.5 Full", "nai-diffusion-4-5-full"],
	["V4.5 Curated", "nai-diffusion-4-5-curated"]
];
var NOVEL_SAMPLERS = [
	"k_euler_ancestral",
	"k_euler",
	"k_dpmpp_2s_ancestral",
	"k_dpmpp_2m",
	"k_dpmpp_sde",
	"k_dpmpp_2m_sde"
];
var NOVEL_SCHEDULES = [
	"karras",
	"exponential",
	"polyexponential"
];
function Novel({ desk, patch }) {
	const setup = desk.novelSetup;
	function set(partial) {
		patch({ novelSetup: {
			...setup,
			...partial
		} });
	}
	const v5 = desk.novelModel.includes("diffusion-5");
	const width = setup.autoSize ? "from character count" : `${setup.width}×${setup.height}`;
	function useAppearance() {
		const text = [
			desk.card.appearance,
			desk.card.name,
			desk.card.scenario
		].map((part) => part.trim()).filter(Boolean).join(", ");
		patch({
			generate: {
				...desk.generate,
				prompt: text
			},
			status: text ? "Appearance is the NovelAI prompt. Draw on the Windows app sends it." : "Write an appearance on the card first."
		});
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: "NovelAI"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-sm text-[var(--muted)]",
				children: "Same page as the Windows NovelAI tab. Draw and Test run there, with this token and these settings. V5 does not use the AMD GPU."
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-4 grid gap-4 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-md border border-[var(--line)] p-3",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "display text-xl",
							children: "Prompt"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
							className: "box mt-2 min-h-40 w-full",
							value: desk.generate.prompt,
							onChange: (event) => patch({ generate: {
								...desk.generate,
								prompt: event.target.value
							} }),
							placeholder: "Age, species, body description, or Danbooru tags"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-2 flex flex-wrap gap-2",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
									onClick: useAppearance,
									children: "Use appearance"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "min-h-11 rounded-md bg-[var(--red)] px-4 text-sm text-white",
									onClick: () => patch({ status: "Draw runs on the Windows app. Open NovelAI there and press Draw. This page keeps the token and the setup." }),
									children: "Draw"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
									onClick: () => patch({ status: "Test NovelAI runs on the Windows app. It checks the persistent token and does not spend Anlas." }),
									children: "Test NovelAI"
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "mt-2 text-xs text-[var(--muted)]",
							children: [
								"Requested size is ",
								width,
								" unless character count changes it. A draw sends Anlas."
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-3 flex min-h-64 items-center justify-center rounded-md border border-[var(--line)] bg-[var(--bg)] px-4 text-center text-sm text-[var(--muted)]",
							children: "The picture lands on the Windows NovelAI tab. Save it there, or use it on the card."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-3 flex flex-wrap gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "min-h-11 flex-1 rounded-md bg-[var(--red)] px-3 text-sm text-white",
								onClick: () => patch({ status: "Save the picture from the Windows NovelAI tab." }),
								children: "Save"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "min-h-11 flex-1 rounded-md border border-[var(--line)] px-3 text-sm",
								onClick: () => patch({ status: "Use on card is on the Windows NovelAI tab, after a picture is drawn." }),
								children: "Use on card"
							})]
						}),
						desk.status ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm text-[var(--muted)]",
							children: desk.status
						}) : null
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid content-start gap-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-md border border-[var(--line)] p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "display text-xl",
								children: "Account"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: ["Persistent token", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "password",
									value: desk.novelToken,
									onChange: (event) => patch({ novelToken: event.target.value })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs text-[var(--muted)]",
								children: "The pst- token stays on this computer and is sent only to NovelAI."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: ["Model", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
									className: "box",
									value: desk.novelModel,
									onChange: (event) => patch({ novelModel: event.target.value }),
									children: NOVEL_MODELS.map(([label, id]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: id,
										children: label
									}, id))
								})]
							})
						]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "rounded-md border border-[var(--line)] p-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between gap-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "display text-xl",
									children: "NovelAI generation setup"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
									onClick: () => set(novelDefaults),
									children: "Reset"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-[var(--muted)]",
								children: "Prompt prefixes, sampler, scheduler, steps, guidance, seed, and resolution."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs text-[var(--muted)]",
								children: "Seed -1 keeps generation random. Any non-negative seed is reused exactly."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid gap-3 sm:grid-cols-2",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
										className: "field",
										children: ["Seed", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
											value: setup.seed,
											onChange: (event) => set({ seed: event.target.value })
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
											className: "mt-3 flex items-center justify-between gap-2",
											children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
												className: "text-sm text-[var(--muted)]",
												children: "Style profile"
											}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
												type: "button",
												className: "min-h-11 rounded-full border border-[var(--line)] px-3 text-xs",
												onClick: () => set({ style: "Anime" }),
												children: "Use Danbooru / Illustrious"
											})]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
											className: "box mt-1 w-full",
											value: setup.style,
											onChange: (event) => set({ style: event.target.value }),
											children: [
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: "Anime" }),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: "Semi-realistic" }),
												/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: "Furry" })
											]
										}),
										/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
											className: "mt-1 text-xs text-[var(--muted)]",
											children: "Suggested from model/source: Danbooru / Illustrious"
										})
									] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
										label: "Steps",
										value: setup.steps,
										onChange: (steps) => set({ steps })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
										label: "Prompt guidance",
										value: setup.guidance,
										step: "0.1",
										onChange: (guidance) => set({ guidance })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
										label: "Guidance rescale",
										value: setup.rescale,
										step: "0.01",
										onChange: (rescale) => set({ rescale })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
										label: "UC preset",
										value: setup.uc,
										onChange: (uc) => set({ uc })
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 text-xs text-[var(--muted)]",
								children: "UC preset: 0 heavy, 1 light, 2 human focus, 3 none, 4 as in your setup."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: ["Prompt prefix", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
									value: setup.prefix,
									onChange: (event) => set({ prefix: event.target.value })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: ["Negative prefix", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
									value: setup.negative,
									onChange: (event) => set({ negative: event.target.value })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid gap-3 sm:grid-cols-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "field",
									children: ["Sampler", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
										className: "box",
										value: setup.sampler,
										onChange: (event) => set({ sampler: event.target.value }),
										children: NOVEL_SAMPLERS.map((name) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: name }, name))
									})]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
									className: "field",
									children: ["Noise schedule", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("select", {
										className: "box",
										value: setup.schedule,
										onChange: (event) => set({ schedule: event.target.value }),
										children: NOVEL_SCHEDULES.map((name) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: name }, name))
									})]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "checkbox",
									checked: setup.autoSize,
									onChange: (event) => set({ autoSize: event.target.checked })
								}), "Choose resolution from character count"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-[var(--muted)]",
								children: "Uses portrait for one subject, square for two, and landscape for three or more. Free-form prompts without a detectable count keep the requested size."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid gap-3 sm:grid-cols-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
									label: "Width",
									value: setup.width,
									onChange: (width) => set({ width })
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
									label: "Height",
									value: setup.height,
									onChange: (height) => set({ height })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-4 flex items-start justify-between gap-2",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
									className: "display text-xl",
									children: "NovelAI V4.5 style plate"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-xs text-[var(--muted)]",
									children: v5 ? "V5 does not take a style plate. Switch to V4.5 to use it." : "A persistent style-only reference applied first to every V4.5 generation, including scenes without characters."
								})] })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: ["Style plate file", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: setup.plate,
									onChange: (event) => set({ plate: event.target.value }),
									placeholder: "Choose image on the Windows tab"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid gap-3 sm:grid-cols-2",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
									label: "Style strength",
									value: setup.strength,
									step: "0.05",
									onChange: (strength) => set({ strength })
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num$1, {
									label: "Style fidelity",
									value: setup.fidelity,
									step: "0.05",
									onChange: (fidelity) => set({ fidelity })
								})]
							})
						]
					})]
				})]
			})
		]
	});
}
var STARTERS = [
	["Night librarian", "A night librarian who shelves books that only exist between midnight and dawn, and already knows the reader's name."],
	["Orbital welder", "An orbital welder who patches the station hull on twelve-hour shifts and talks to the dark like it might answer."],
	["Last dragon", "The last dragon in a drowned valley, keeping a human village because the old bargain still stands."],
	["Dock rigger", "A dock rigger who can tell a ship's cargo by the way it sits in the water, and who does not ask questions."],
	["Flood courier", "A flood courier who carries letters across a city that is slowly going under, and never opens them."],
	["Quiet archivist", "A quiet archivist of other people's secrets, paid to remember what the city would rather lose."],
	["Train cook", "A train cook on a line that no longer appears on maps, feeding whoever is still riding."],
	["Lighthouse keeper", "A lighthouse keeper on a coast where the light is for something that is not ships."],
	["Map mender", "A map mender who stitches streets back onto paper after the city rearranges itself overnight."],
	["Garden locksmith", "A garden locksmith who makes keys for gates that only open for one person, once."]
];
var FIELDS = [
	{
		key: "description",
		label: "Description",
		hint: "Identity and role. Marinara sends this every turn.",
		rows: 6
	},
	{
		key: "personality",
		label: "Personality",
		hint: "Speech, temperament, and habits. Specific beats a pile of adjectives.",
		rows: 5
	},
	{
		key: "backstory",
		label: "Backstory",
		hint: "Marinara extension. Origin, relationships, facts that stay true.",
		rows: 5
	},
	{
		key: "appearance",
		label: "Appearance",
		hint: "Marinara extension. Face, build, clothes, and visual detail.",
		rows: 5
	},
	{
		key: "scenario",
		label: "Scenario",
		hint: "The situation a new chat starts in.",
		rows: 4
	},
	{
		key: "first_mes",
		label: "First message",
		hint: "The opening. Actions in asterisks.",
		rows: 5
	},
	{
		key: "mes_example",
		label: "Examples",
		hint: "Separate exchanges with <START>. Teaches the voice.",
		rows: 5
	},
	{
		key: "creator_notes",
		label: "Creator notes",
		hint: "For people reading the card. Not sent to the model.",
		rows: 3
	},
	{
		key: "system_prompt",
		label: "System prompt",
		hint: "Optional. Leave blank to keep Marinara's own instructions.",
		rows: 4
	},
	{
		key: "post_history_instructions",
		label: "After history",
		hint: "Optional instructions placed after the chat log.",
		rows: 4
	}
];
function words(text) {
	const count = text.trim() ? text.trim().split(/\s+/).length : 0;
	return `${count} word${count === 1 ? "" : "s"}`;
}
function bump(version) {
	const match = version.match(/^(\d+)\.(\d+)/);
	if (!match) return "1.1";
	return `${match[1]}.${Number(match[2]) + 1}`;
}
function CardDesk({ desk, patch, patchCard, busy, extras, onWrite, onRewrite, onOpen, onRemove, onKeep, onNew, onJson, onPng, onCopy, onImport }) {
	const [order, setOrder] = (0, import_react.useState)(STARTERS);
	const rows = desk.mode === "personas" || desk.personaMode ? desk.personas.map((row) => ({
		...row,
		favorite: false,
		portrait: ""
	})) : desk.library;
	const personaId = desk.activePersona;
	const sheetName = desk.card.name.trim() || "Unnamed";
	const nameColor = desk.look.nameColor || "var(--accent)";
	const dialogue = desk.look.dialogue || "var(--ink)";
	const box = desk.look.messageBox || "var(--paper)";
	const book = (0, import_react.useMemo)(() => desk.lorebooks.find((item) => item.id === desk.linkedBook), [desk.lorebooks, desk.linkedBook]);
	function addFiles(list) {
		const files = Array.from(list ?? []).filter((file) => file.type.startsWith("image/")).slice(0, Math.max(0, 200 - desk.references.length));
		if (!files.length) return;
		Promise.all(files.map((file) => new Promise((resolve) => {
			const reader = new FileReader();
			reader.onload = () => resolve({
				id: crypto.randomUUID(),
				name: file.name,
				url: String(reader.result || "")
			});
			reader.readAsDataURL(file);
		}))).then((pics) => {
			const first = pics[0];
			patch({
				references: [...desk.references, ...pics].slice(0, 200),
				starredRef: desk.starredRef || first.id,
				portrait: desk.portrait || first.url,
				status: "Reference added. The starred picture is the portrait."
			});
		});
	}
	function star(pic) {
		patch({
			starredRef: pic.id,
			portrait: pic.url,
			status: "That picture is the portrait."
		});
	}
	async function testKobold() {
		patch({ status: "Checking Kobold…" });
		try {
			const response = await fetch(`${koboldRoot(desk.kobold)}/models`);
			patch({ status: response.ok ? "Kobold answered." : `Kobold returned HTTP ${response.status}.` });
		} catch {
			patch({ status: "Could not reach KoboldCPP. It has to be running on this computer." });
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "desk-columns",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "desk-col",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Concept" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
								value: desk.concept,
								placeholder: "Who are they, where are they, and what should a chat feel like?",
								onChange: (event) => patch({ concept: event.target.value })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								className: "btn-accent",
								style: { marginTop: "0.8rem" },
								disabled: busy,
								onClick: onWrite,
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RefreshCw, { size: 16 }), " Write the card"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "check",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "checkbox",
									checked: desk.fillEmpty,
									onChange: (event) => patch({ fillEmpty: event.target.checked })
								}), "Fill empty fields only"]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "kicker",
								style: { marginTop: "1.1rem" },
								children: "Starters"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								className: "btn-quiet block",
								style: { marginTop: "0.55rem" },
								onClick: () => setOrder((current) => [...current].sort(() => Math.random() - .5)),
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Shuffle, { size: 16 }), " Randomize starters"]
							}),
							order.map(([title, concept]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "btn-quiet block",
								style: { marginTop: "0.45rem" },
								onClick: () => patch({ concept }),
								children: title
							}, title))
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "References" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "drop",
								onDragOver: (event) => event.preventDefault(),
								onDrop: (event) => {
									event.preventDefault();
									addFiles(event.dataTransfer.files);
								},
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ImagePlus, {
										size: 18,
										style: { margin: "0 auto 0.35rem" }
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("br", {}),
									"Drop pictures, or click to upload"
								] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "file",
									accept: "image/png,image/jpeg,image/webp",
									multiple: true,
									className: "sr-only",
									onChange: (event) => {
										addFiles(event.target.files);
										event.target.value = "";
									}
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "Up to 200. They stay with this card. A vision model can read them when you write the card. The starred one is the portrait."
							}),
							desk.references.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "No reference pictures yet."
							}) : null,
							desk.references.map((pic) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "ref-row",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
										src: pic.url,
										alt: "",
										style: {
											width: "2.2rem",
											height: "2.2rem",
											objectFit: "cover",
											borderRadius: "0.4rem"
										}
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										className: "name",
										onClick: () => star(pic),
										children: pic.name
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										className: "icon-btn",
										"aria-label": "Use as portrait",
										onClick: () => star(pic),
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Star, {
											size: 16,
											fill: desk.starredRef === pic.id ? "currentColor" : "none"
										})
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										className: "icon-btn",
										"aria-label": "Remove picture",
										onClick: () => patch({ references: desk.references.filter((item) => item.id !== pic.id) }),
										children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { size: 16 })
									})
								]
							}, pic.id)),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "check",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "checkbox",
									checked: desk.sendRefs,
									onChange: (event) => patch({ sendRefs: event.target.checked })
								}), "Send pictures to the model"]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "KoboldCPP" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "OpenAI endpoint"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: desk.kobold,
									onChange: (event) => patch({ kobold: event.target.value }),
									placeholder: "http://localhost:5001"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "Usually http://127.0.0.1:5001/v1. The Windows app talks to Kobold on your PC. This preview can only reach it when Kobold is running on the same computer."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Password, if you set one"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "password",
									value: desk.koboldKey,
									onChange: (event) => patch({ koboldKey: event.target.value })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "kicker",
									children: ["Temperature ", desk.writerTemp.toFixed(2)]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "range",
									min: 0,
									max: 2,
									step: .05,
									value: desk.writerTemp,
									onChange: (event) => patch({ writerTemp: Number(event.target.value) })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Max tokens"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "number",
									min: 64,
									max: 32e3,
									value: desk.writerMax,
									onChange: (event) => patch({ writerMax: Number(event.target.value) || 0 })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "btn-quiet block",
								style: { marginTop: "0.7rem" },
								onClick: () => void testKobold(),
								children: "Test connection"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Library" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "actions",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "btn-quiet",
									onClick: onKeep,
									children: "Keep"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									type: "button",
									className: "btn-quiet",
									onClick: onNew,
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Plus, { size: 16 }), " New"]
								})]
							}),
							rows.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "Nothing saved yet."
							}) : null,
							rows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "library-row",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "name",
									onClick: () => onOpen(row),
									children: row.card.name || "Unnamed"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "icon-btn",
									"aria-label": `Remove ${row.card.name || "card"}`,
									onClick: () => onRemove(row.id),
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trash2, { size: 16 })
								})]
							}, row.id))
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "desk-col",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
						className: "slab",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "pair",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								style: { marginTop: 0 },
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Name"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: desk.card.name,
									onChange: (event) => patchCard({ name: event.target.value })
								})]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								style: { marginTop: 0 },
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Summary"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: desk.card.summary,
									onChange: (event) => patchCard({ summary: event.target.value })
								})]
							})]
						})
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Version" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "Keeping this card again saves the previous copy and raises the version."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Saved copies"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "box",
									value: "current",
									onChange: (event) => {
										const snap = desk.versions.find((item) => item.id === event.target.value);
										if (snap?.card) patch({
											card: snap.card,
											status: `Restored the ${snap.version} copy.`
										});
									},
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("option", {
										value: "current",
										children: ["This card · ", desk.card.character_version || "1.0"]
									}), desk.versions.map((snap) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("option", {
										value: snap.id,
										disabled: !snap.card,
										children: [
											snap.version,
											" · ",
											snap.note || snap.at
										]
									}, snap.id))]
								})]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Creator" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "Who made this card. You can type a name, or use a persona."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Name"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: desk.card.creator,
									onChange: (event) => patchCard({ creator: event.target.value })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Persona"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "box",
									value: personaId,
									onChange: (event) => patch({ activePersona: event.target.value }),
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "",
										children: "No persona selected"
									}), desk.personas.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("option", {
										value: row.id,
										children: ["Persona in the editor · ", row.card.name || "Unnamed"]
									}, row.id))]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "btn-quiet block",
								style: { marginTop: "0.7rem" },
								disabled: !personaId,
								onClick: () => {
									const row = desk.personas.find((item) => item.id === personaId);
									if (row) patchCard({ creator: row.card.name || desk.card.creator });
								},
								children: "Use this persona"
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Chat colors" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "These colors travel with the card and color this character's messages. Empty dialogue uses the default. Empty box uses the sheet."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ColorField, {
								label: "Name color",
								value: desk.look.nameColor,
								placeholder: "#e8b86d",
								onChange: (nameColor) => patch({ look: {
									...desk.look,
									nameColor
								} })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ColorField, {
								label: "Dialogue color",
								value: desk.look.dialogue,
								placeholder: "Empty uses the Colors default",
								onChange: (dialogue) => patch({ look: {
									...desk.look,
									dialogue
								} })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ColorField, {
								label: "Box color",
								value: desk.look.messageBox,
								placeholder: "Empty uses the chat paper",
								onChange: (messageBox) => patch({ look: {
									...desk.look,
									messageBox
								} })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "sample",
								style: {
									background: box,
									color: dialogue
								},
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", {
									style: { color: nameColor },
									children: sheetName === "Unnamed" ? "Character" : sheetName
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									style: { margin: 0 },
									children: "They look over. \"Stay close.\" *A lamp flickers.*"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Aliases"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
									style: { minHeight: "4.5rem" },
									value: desk.card.aliases,
									placeholder: "Other names, one per line. Used when you write who should answer.",
									onChange: (event) => patchCard({ aliases: event.target.value })
								})]
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
						className: "slab",
						children: [
							FIELDS.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								style: { marginTop: "1.1rem" },
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
										style: {
											display: "flex",
											justifyContent: "space-between",
											alignItems: "center",
											gap: "0.5rem"
										},
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
											className: "kicker",
											children: field.label
										}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
											type: "button",
											className: "rewrite",
											disabled: busy,
											onClick: () => onRewrite(field.key, field.label),
											children: "Rewrite"
										})]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
										rows: field.rows,
										value: String(desk.card[field.key] ?? ""),
										onChange: (event) => patchCard({ [field.key]: event.target.value })
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
										className: "hint",
										children: [
											field.hint,
											" · ",
											words(String(desk.card[field.key] ?? ""))
										]
									})
								]
							}, field.key)),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Tags"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									value: desk.card.tags.join(", "),
									placeholder: "original, slow-burn, city",
									onChange: (event) => patchCard({ tags: event.target.value.split(",").map((item) => item.trim()) })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								style: {
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									marginTop: "1rem"
								},
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Alternate greetings"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
									type: "button",
									className: "icon-btn",
									"aria-label": "Add greeting",
									onClick: () => patchCard({ alternate_greetings: [...desk.card.alternate_greetings, ""] }),
									children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Plus, { size: 16 })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: "The first message is greeting 1. Each box is another opening you can swipe to in chat."
							}),
							desk.card.alternate_greetings.map((greeting, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
								value: greeting,
								onChange: (event) => patchCard({ alternate_greetings: desk.card.alternate_greetings.map((item, itemIndex) => itemIndex === index ? event.target.value : item) })
							}, index)),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "kicker",
									children: ["Talkativeness ", desk.card.talkativeness]
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "range",
									min: 0,
									max: 100,
									value: desk.card.talkativeness,
									onChange: (event) => patchCard({ talkativeness: Number(event.target.value) })
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "field",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "kicker",
									children: "Linked lorebook"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
									className: "box",
									value: desk.linkedBook,
									onChange: (event) => patch({ linkedBook: event.target.value }),
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: "",
										children: "None"
									}), desk.lorebooks.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
										value: item.id,
										children: item.name
									}, item.id))]
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: book ? `${book.name} is packed into new chats with this card.` : "New chats with this card include that lorebook. World books are chosen inside the chat."
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "actions",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										type: "button",
										className: "btn-accent",
										onClick: onJson,
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { size: 16 }), " Download JSON"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										type: "button",
										className: "btn-quiet",
										onClick: onPng,
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { size: 16 }), " Download PNG"]
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
										type: "button",
										className: "btn-quiet",
										onClick: onCopy,
										children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Copy, { size: 16 }), " Copy JSON"]
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "btn-quiet",
								style: { marginTop: "0.5rem" },
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Upload, { size: 16 }),
									" Import",
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
										type: "file",
										accept: "application/json,.json,.png",
										className: "sr-only",
										onChange: (event) => onImport(event.target.files?.[0])
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "hint",
								children: desk.status
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("details", {
						className: "slab",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("summary", {
							className: "kicker",
							children: "More card tools"
						}), extras]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "desk-col",
				"aria-label": "Character sheet",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
					className: "sheet",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "kicker",
							children: "Character sheet"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: sheetName }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: desk.card.summary.trim() || "No summary yet." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("hr", { className: "rule" }),
						desk.card.description.trim() ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "prose",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", { children: "Description" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: desk.card.description })]
						}) : null,
						desk.card.personality.trim() ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "prose",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", { children: "Personality" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: desk.card.personality })]
						}) : null,
						desk.card.scenario.trim() ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "prose",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", { children: "Scenario" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: desk.card.scenario })]
						}) : null,
						desk.card.first_mes.trim() ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "prose",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", { children: "First message" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: desk.card.first_mes })]
						}) : null
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "hint",
					style: { margin: "0.8rem 0.2rem 0" },
					children: "Backstory and appearance live in Marinara's extensions. A PNG download uses the portrait and hides the same card inside the file."
				})]
			})
		]
	});
}
function ColorField({ label, value, placeholder, onChange }) {
	const hex = /^#[0-9a-fA-F]{6}$/.test(value) ? value : "#e8b86d";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "field",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "kicker",
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "swatch",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "color",
				value: hex,
				"aria-label": label,
				onChange: (event) => onChange(event.target.value)
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value,
				placeholder,
				onChange: (event) => onChange(event.target.value)
			})]
		})]
	});
}
var themeFields = [
	["bg", "Background"],
	["surface", "Panels"],
	["inset", "Fields"],
	["fg", "Text"],
	["muted", "Muted text"],
	["line", "Lines"],
	["accent", "Accent"],
	["accentInk", "Text on accent"],
	["paper", "Character sheet"],
	["ink", "Sheet text"],
	["gold", "Sheet rule"]
];
var KEY = "redwright-theme";
var cardwrightTheme = {
	bg: "#16080a",
	surface: "#2a1214",
	inset: "#140709",
	fg: "#f6eee8",
	muted: "#b39b94",
	line: "#5a3330",
	accent: "#e39b88",
	accentInk: "#2a1210",
	paper: "#e6e1dc",
	ink: "#1c1210",
	gold: "#d4a574",
	radius: 22,
	buttonRadius: 999,
	size: 16,
	font: "cardwright",
	customFont: "",
	extraCss: ""
};
var themePresets = [
	{
		name: "Cardwright",
		theme: cardwrightTheme
	},
	{
		name: "RedWright",
		theme: {
			...cardwrightTheme,
			bg: "#12110f",
			surface: "#1c1a17",
			inset: "#0e0d0b",
			fg: "#f4efe6",
			muted: "#a39b90",
			line: "#3a342c",
			accent: "#e23d2b",
			accentInk: "#fff8f4",
			paper: "#f3ead7",
			ink: "#241c16",
			gold: "#e23d2b",
			radius: 12,
			buttonRadius: 10
		}
	},
	{
		name: "Paper",
		theme: {
			...cardwrightTheme,
			bg: "#efe4d4",
			surface: "#f7f1e6",
			inset: "#fffaf3",
			fg: "#241c16",
			muted: "#6d5c50",
			line: "#ddcbb6",
			accent: "#c45c3e",
			accentInk: "#fff8f4",
			paper: "#fffdf8",
			ink: "#241c16",
			gold: "#c45c3e",
			radius: 18
		}
	},
	{
		name: "Night",
		theme: {
			...cardwrightTheme,
			bg: "#0c1016",
			surface: "#161c27",
			inset: "#0a0e14",
			fg: "#e7eef8",
			muted: "#93a0b5",
			line: "#2c384c",
			accent: "#8eb6ff",
			accentInk: "#0c1016",
			paper: "#dfe7f2",
			ink: "#121820",
			gold: "#8eb6ff"
		}
	}
];
function stacks(theme) {
	if (theme.font === "custom" && theme.customFont.trim()) {
		const family = theme.customFont.trim().replace(/[;{}]/g, "");
		return {
			ui: family,
			display: family
		};
	}
	if (theme.font === "system") return {
		ui: "\"Segoe UI\", sans-serif",
		display: "Palatino, Georgia, serif"
	};
	if (theme.font === "serif") return {
		ui: "Georgia, \"Iowan Old Style\", serif",
		display: "Georgia, \"Iowan Old Style\", serif"
	};
	if (theme.font === "mono") return {
		ui: "ui-monospace, \"Cascadia Code\", monospace",
		display: "ui-monospace, monospace"
	};
	return {
		ui: "\"Outfit\", \"Avenir Next\", \"Segoe UI\", sans-serif",
		display: "\"Fraunces\", \"Iowan Old Style\", Palatino, serif"
	};
}
function applyTheme(theme) {
	if (typeof document === "undefined") return;
	const root = document.documentElement;
	const font = stacks(theme);
	const values = {
		"--bg": theme.bg,
		"--surface": theme.surface,
		"--inset": theme.inset,
		"--fg": theme.fg,
		"--muted": theme.muted,
		"--line": theme.line,
		"--red": theme.accent,
		"--accent": theme.accent,
		"--accent-ink": theme.accentInk,
		"--paper": theme.paper,
		"--ink": theme.ink,
		"--gold": theme.gold,
		"--radius": `${theme.radius}px`,
		"--btn-radius": `${theme.buttonRadius}px`,
		"--font-ui": font.ui,
		"--font-display": font.display
	};
	for (const [key, value] of Object.entries(values)) root.style.setProperty(key, value);
	root.style.fontSize = `${theme.size}px`;
	document.getElementById("theme-extra")?.remove();
	const css = theme.extraCss.replace(/<\/style/gi, "").trim();
	if (css) {
		const style = document.createElement("style");
		style.id = "theme-extra";
		style.textContent = css;
		document.head.appendChild(style);
	}
}
function loadTheme() {
	if (typeof window === "undefined") return cardwrightTheme;
	try {
		const raw = localStorage.getItem(KEY);
		if (!raw) return cardwrightTheme;
		const parsed = JSON.parse(raw);
		return {
			...cardwrightTheme,
			...parsed
		};
	} catch {
		return cardwrightTheme;
	}
}
function saveTheme(theme) {
	localStorage.setItem(KEY, JSON.stringify(theme));
}
function ThemePanel({ theme, onChange }) {
	function set(key, value) {
		onChange({
			...theme,
			[key]: value
		});
	}
	function copy() {
		navigator.clipboard?.writeText(JSON.stringify(theme, null, 2));
	}
	function read(file) {
		if (!file) return;
		file.text().then((text) => onChange({
			...theme,
			...JSON.parse(text)
		})).catch(() => void 0);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "slab",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "kicker",
						children: "Theme"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "App theme" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "hint",
						children: "Every color, the type, and the shape apply to the whole studio. The character sheet uses the paper colors."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
						className: "actions",
						children: themePresets.map((preset) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
							type: "button",
							className: "btn-quiet",
							onClick: () => onChange({
								...preset.theme,
								extraCss: theme.extraCss
							}),
							children: preset.name
						}, preset.name))
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "slab",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "kicker",
					children: "Colors"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "theme-grid",
					children: themeFields.map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "swatch",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "color",
								value: /^#[0-9a-fA-F]{6}$/.test(theme[key]) ? theme[key] : "#000000",
								onChange: (event) => set(key, event.target.value),
								"aria-label": label
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								value: theme[key],
								onChange: (event) => set(key, event.target.value)
							})]
						})]
					}, key))
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "slab",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "kicker",
						children: "Type and shape"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["Font", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
							className: "box",
							value: theme.font,
							onChange: (event) => set("font", event.target.value),
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "cardwright",
									children: "Outfit and Fraunces"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "system",
									children: "System"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "serif",
									children: "Serif"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "mono",
									children: "Mono"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "custom",
									children: "Custom family"
								})
							]
						})]
					}),
					theme.font === "custom" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: ["Font family", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							value: theme.customFont,
							placeholder: "Georgia, serif",
							onChange: (event) => set("customFont", event.target.value)
						})]
					}) : null,
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: [
							"Text size ",
							theme.size,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "range",
								min: 13,
								max: 20,
								value: theme.size,
								onChange: (event) => set("size", Number(event.target.value))
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: [
							"Panel corners ",
							theme.radius,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "range",
								min: 0,
								max: 32,
								value: theme.radius,
								onChange: (event) => set("radius", Number(event.target.value))
							})
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
						className: "field",
						children: [
							"Button corners ",
							theme.buttonRadius,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "range",
								min: 0,
								max: 999,
								value: theme.buttonRadius,
								onChange: (event) => set("buttonRadius", Number(event.target.value))
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "slab",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "kicker",
						children: "Your CSS"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "hint",
						children: "Optional rules on top of the colors. They stay on this computer."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
						className: "inset",
						value: theme.extraCss,
						placeholder: ".slab { box-shadow: none; }",
						onChange: (event) => set("extraCss", event.target.value)
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "actions",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "btn-accent",
								onClick: () => onChange({ ...themePresets[0].theme }),
								children: "Reset"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
								type: "button",
								className: "btn-quiet",
								onClick: copy,
								children: "Copy JSON"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
								className: "btn-quiet",
								children: ["Import", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
									type: "file",
									accept: "application/json,.json",
									className: "sr-only",
									onChange: (event) => read(event.target.files?.[0])
								})]
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "slab",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "kicker",
						children: "Preview"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("article", {
						className: "sheet",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "kicker",
								children: "Character sheet"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: "Unnamed" }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "No summary yet." }),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("hr", { className: "rule" })
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "btn-accent",
						style: { marginTop: "0.8rem" },
						children: "Write the card"
					})
				]
			})
		]
	});
}
var BUILD = "7";
function putCard(current, card, fresh, status) {
	const persona = current.personaMode || current.mode === "personas";
	const id = !fresh && current.openCardId ? current.openCardId : crypto.randomUUID();
	if (persona) {
		const row = {
			id,
			card,
			title: current.title,
			concept: current.concept
		};
		return {
			...current,
			card,
			openCardId: id,
			personas: [row, ...current.personas.filter((item) => item.id !== id)].slice(0, 200),
			status: status ?? current.status
		};
	}
	const row = {
		id,
		card,
		title: current.title,
		favorite: current.favorite,
		portrait: current.portrait,
		concept: current.concept
	};
	return {
		...current,
		card,
		openCardId: id,
		library: [row, ...current.library.filter((item) => item.id !== id)].slice(0, 200),
		status: status ?? current.status
	};
}
var TOP = [
	["characters", "Characters"],
	["personas", "Personas"],
	["chat", "Chat"],
	["lorebooks", "Lorebooks"],
	["pictures", "Pictures"],
	["library", "Library"],
	["life", "Life"],
	["presets", "Presets"],
	["novel", "NovelAI"],
	["theme", "Theme"]
];
var PICTURES = [
	["generate", "Generate"],
	["library", "Library"],
	["captions", "Captions"],
	["train", "Train"]
];
function Studio() {
	const [desk, setDesk] = (0, import_react.useState)(blankDesk);
	const [theme, setTheme] = (0, import_react.useState)(() => loadTheme());
	const [ready, setReady] = (0, import_react.useState)(false);
	const [busy, setBusy] = (0, import_react.useState)(false);
	(0, import_react.useEffect)(() => {
		applyTheme(theme);
		saveTheme(theme);
	}, [theme]);
	(0, import_react.useEffect)(() => {
		const loaded = loadDesk();
		if (!loaded.characterId) loaded.characterId = crypto.randomUUID();
		setDesk(loaded);
		setReady(true);
	}, []);
	(0, import_react.useEffect)(() => {
		if (ready) saveDesk(desk);
	}, [desk, ready]);
	function patch(partial) {
		setDesk((current) => ({
			...current,
			...partial
		}));
	}
	function patchCard(partial) {
		setDesk((current) => ({
			...current,
			card: {
				...current.card,
				...partial
			}
		}));
	}
	function note(status) {
		patch({ status });
	}
	function openSaved(row) {
		patch({
			card: row.card,
			title: row.title,
			favorite: row.favorite ?? false,
			portrait: row.portrait ?? "",
			concept: row.concept ?? desk.concept,
			openCardId: row.id,
			greetings: row.card.alternate_greetings.join("\n---\n"),
			editorTab: "card",
			status: `Opened ${row.card.name || "the card"}.`
		});
	}
	function removeSaved(id) {
		setDesk((current) => {
			const status = "Removed that card from the library.";
			if (current.personaMode || current.mode === "personas") return {
				...current,
				personas: current.personas.filter((item) => item.id !== id),
				openCardId: current.openCardId === id ? "" : current.openCardId,
				status
			};
			return {
				...current,
				library: current.library.filter((item) => item.id !== id),
				openCardId: current.openCardId === id ? "" : current.openCardId,
				status
			};
		});
	}
	async function write() {
		setBusy(true);
		const persona = desk.personaMode || desk.mode === "personas";
		note(persona ? "Writing the persona…" : "Writing the card…");
		try {
			let concept = desk.concept;
			if (desk.sendRefs && desk.references.length) concept += `\n\n${desk.references.length} reference pictures belong to this character. The starred picture is the portrait. Match the appearance to it.`;
			const written = await writeCard(desk.kobold, desk.koboldKey, concept, persona, {
				temperature: desk.writerTemp,
				maxTokens: desk.writerMax
			});
			setDesk((current) => {
				const previous = current.card;
				const next = { ...written };
				if (current.fillEmpty) {
					for (const key of [
						"name",
						"summary",
						"description",
						"personality",
						"scenario",
						"first_mes",
						"mes_example",
						"creator_notes",
						"system_prompt",
						"post_history_instructions",
						"creator",
						"backstory",
						"appearance",
						"aliases",
						"long_memory"
					]) if (previous[key].trim()) next[key] = previous[key];
					if (previous.tags.some((tag) => tag.trim())) next.tags = previous.tags;
					if (previous.alternate_greetings.some((item) => item.trim())) next.alternate_greetings = previous.alternate_greetings;
				}
				const had = Boolean(previous.name.trim() || previous.summary.trim() || previous.description.trim());
				const versions = had ? [{
					id: crypto.randomUUID(),
					version: previous.character_version || "1.0",
					at: (/* @__PURE__ */ new Date()).toLocaleString(),
					note: previous.summary.slice(0, 80) || previous.name || "Saved copy",
					card: previous
				}, ...current.versions].slice(0, 20) : current.versions;
				if (had && !current.fillEmpty) next.character_version = bump(previous.character_version || "1.0");
				return putCard({
					...current,
					versions,
					greetings: next.alternate_greetings.join("\n---\n")
				}, next, !had, "Wrote the card and saved it to the library.");
			});
		} catch (error) {
			note(error instanceof Error ? error.message : "Could not write the card.");
		} finally {
			setBusy(false);
		}
	}
	async function rewrite(field, label) {
		setBusy(true);
		note(`Rewriting ${label}…`);
		try {
			const text = await rewriteField(desk.kobold, desk.koboldKey, label, desk.concept, {
				temperature: desk.writerTemp,
				maxTokens: desk.writerMax
			});
			setDesk((current) => putCard(current, {
				...current.card,
				[field]: text
			}, false, `Filled ${label} from the prompt and saved the card.`));
		} catch (error) {
			note(error instanceof Error ? error.message : "Could not rewrite that field.");
		} finally {
			setBusy(false);
		}
	}
	function importCard(file) {
		if (!file) return;
		file.text().then((text) => {
			const card = normalizeCard(JSON.parse(text));
			patch({
				card,
				greetings: card.alternate_greetings.join("\n---\n"),
				status: `Imported ${card.name || "the card"}.`
			});
		}).catch(() => note("That file is not a character card."));
	}
	function newCard() {
		patch({
			card: blankCard(),
			concept: "",
			openCardId: "",
			title: "",
			portrait: "",
			references: [],
			starredRef: "",
			greetings: "",
			status: "Started a new card."
		});
	}
	async function copyJson() {
		const greetings = desk.greetings.split(/\n---\n/).map((item) => item.trim()).filter(Boolean);
		const card = {
			...desk.card,
			alternate_greetings: desk.card.alternate_greetings.filter((item) => item.trim()) || greetings
		};
		try {
			await navigator.clipboard.writeText(JSON.stringify(v2(card, desk), null, 2));
			note("Copied the card JSON.");
		} catch {
			note("Could not copy the card.");
		}
	}
	function keepInLibrary() {
		const id = crypto.randomUUID();
		const row = {
			id,
			card: desk.card,
			title: desk.title,
			favorite: desk.favorite,
			portrait: desk.portrait,
			concept: desk.concept
		};
		if (desk.mode === "personas" || desk.personaMode) {
			patch({
				personas: [{
					id,
					card: desk.card,
					title: desk.title,
					concept: desk.concept
				}, ...desk.personas],
				openCardId: id,
				status: "Kept the persona."
			});
			return;
		}
		patch({
			library: [row, ...desk.library],
			openCardId: id,
			status: "Kept the card in the library."
		});
	}
	async function saveJson() {
		const greetings = desk.greetings.split(/\n---\n/).map((item) => item.trim()).filter(Boolean);
		const card = {
			...desk.card,
			tags: desk.card.tags.filter((tag) => tag.trim()),
			alternate_greetings: desk.card.alternate_greetings.filter((item) => item.trim()).length ? desk.card.alternate_greetings.filter((item) => item.trim()) : greetings
		};
		download(`${slug(card.name)}.json`, new Blob([JSON.stringify(v2(card, desk), null, 2)], { type: "application/json" }));
		note("Saved a Character Card V2 file. Marinara imports it as JSON.");
	}
	async function savePng() {
		setBusy(true);
		try {
			const blob = desk.portrait ? await (await fetch(desk.portrait)).blob() : null;
			download(`${slug(desk.card.name)}.png`, await packPng({ ...desk.card }, blob));
			note(blob ? "Saved a PNG card with the portrait inside." : "Saved a PNG card on a text plate.");
		} catch (error) {
			note(error instanceof Error ? error.message : "Could not pack the PNG.");
		} finally {
			setBusy(false);
		}
	}
	function readImage(file, into) {
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			const url = String(reader.result || "");
			if (into === "portrait") patch({
				portrait: url,
				status: "Portrait attached."
			});
			else patch({
				gallery: [url, ...desk.gallery].slice(0, 8),
				status: "Added to the gallery."
			});
		};
		reader.readAsDataURL(file);
	}
	const prompt = picturePrompt(desk.card);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "shell",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "topnav",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", {
						className: "display text-xl",
						children: "RedWright"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
						className: "mr-2 text-xs text-[var(--muted)]",
						children: ["build ", BUILD]
					}),
					TOP.map(([id, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						onClick: () => patch({ mode: id }),
						className: `nav-btn ${desk.mode === id ? "on" : ""}`,
						children: label
					}, id))
				]
			}),
			desk.mode === "characters" || desk.mode === "personas" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardDesk, {
				desk,
				patch,
				patchCard,
				busy,
				onWrite: () => void write(),
				onRewrite: (field, label) => void rewrite(field, label),
				onOpen: openSaved,
				onRemove: removeSaved,
				onKeep: keepInLibrary,
				onNew: newCard,
				onJson: () => void saveJson(),
				onPng: () => void savePng(),
				onCopy: () => void copyJson(),
				onImport: importCard,
				extras: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Onboarding, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Metadata, {
						desk,
						patch,
						patchCard
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Convo, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Lore, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Sprites, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Gallery, {
						desk,
						onFile: (file) => readImage(file, "gallery")
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Colors, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Voice, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatsPanel, {
						desk,
						patch
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Advanced, {
						desk,
						patch,
						patchCard
					})
				] })
			}) : null,
			desk.mode === "theme" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mode-scroll",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ThemePanel, {
					theme,
					onChange: setTheme
				})
			}),
			desk.mode === "chat" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Chat, {
				desk,
				patch,
				busy,
				setBusy
			}),
			desk.mode === "lorebooks" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Lorebooks, {
				desk,
				patch
			}),
			desk.mode === "life" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Life, {
				desk,
				patch
			}),
			desk.mode === "presets" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Presets, {
				desk,
				patch
			}),
			desk.mode === "novel" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Novel, {
				desk,
				patch
			}),
			desk.mode === "pictures" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "work",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
					className: "rail",
					"aria-label": "Picture tools",
					children: PICTURES.map(([id, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						onClick: () => patch({ pictureTab: id }),
						className: `nav-btn ${desk.pictureTab === id ? "on" : ""}`,
						children: label
					}, id))
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "pane",
					children: [
						desk.pictureTab === "generate" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Generate, {
							desk,
							patch,
							cardPrompt: prompt
						}),
						desk.pictureTab === "library" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(PictureLibrary, {
							desk,
							patch
						}),
						desk.pictureTab === "captions" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Captions, {
							desk,
							patch
						}),
						desk.pictureTab === "train" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Train, {
							desk,
							patch
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-4 text-sm text-[var(--muted)]",
							children: desk.status
						})
					]
				})]
			}),
			desk.mode === "library" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Library, {
				desk,
				patch
			})
		]
	});
}
function v2(card, desk) {
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
			creator: card.creator || "Cardwright",
			character_version: card.character_version || "1.0",
			alternate_greetings: card.alternate_greetings,
			character_book: (() => {
				const linked = desk.lorebooks.find((item) => item.id === desk.linkedBook);
				const entries = linked?.entries?.length ? linked.entries : desk.lore;
				return entries.length ? {
					name: linked?.name || `${card.name || "Card"} lore`,
					entries: entries.map((entry, index) => ({
						id: index,
						keys: entry.keys.split(",").map((key) => key.trim()).filter(Boolean),
						content: entry.content,
						enabled: entry.enabled,
						insertion_order: index
					}))
				} : null;
			})(),
			extensions: {
				talkativeness: card.talkativeness,
				fav: desk.favorite,
				backstory: card.backstory,
				appearance: card.appearance,
				aliases: card.aliases,
				long_memory: [card.long_memory, ...desk.life.map((beat) => [
					beat.when,
					beat.title,
					beat.body
				].filter(Boolean).join(" — "))].filter(Boolean).join("\n"),
				title: desk.title,
				chat_look: desk.look,
				voice: desk.voice,
				phonetic_name: desk.phonetic,
				stats: desk.stats,
				rpg: desk.rpg,
				pools: desk.pools,
				attributes: desk.attrs,
				persona_bars: desk.personaBars,
				depth_prompt: {
					prompt: desk.depthPrompt,
					depth: desk.depth,
					role: desk.depthRole
				},
				image_override: desk.imageOverride,
				image_tags: desk.imageTags,
				onboarding: desk.onboarding,
				convo: desk.convo,
				sprites: desk.sprites,
				sprite_layout: desk.spriteLayout,
				regex_scripts: desk.regex,
				character_id: desk.characterId
			}
		}
	};
}
function Metadata({ desk, patch, patchCard }) {
	const [tag, setTag] = (0, import_react.useState)("");
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Character ID", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				readOnly: true,
				value: desk.characterId
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => void navigator.clipboard.writeText(desk.characterId),
			children: "Copy ID"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Creator", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: desk.card.creator,
				onChange: (event) => patchCard({ creator: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Version", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: desk.card.character_version,
				onChange: (event) => patchCard({ character_version: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: desk.autoVersion,
				onChange: (event) => patch({ autoVersion: event.target.checked })
			}), "Automatic versioning"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: [
				"Talkativeness ",
				desk.card.talkativeness,
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					type: "range",
					min: 0,
					max: 100,
					value: desk.card.talkativeness,
					onChange: (event) => patchCard({ talkativeness: Number(event.target.value) })
				})
			]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-3 flex flex-wrap gap-2",
			children: desk.card.tags.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => patchCard({ tags: desk.card.tags.filter((tagName) => tagName !== item) }),
				children: [item, " ×"]
			}, item))
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 flex flex-wrap gap-2",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					className: "box max-w-xs",
					value: tag,
					placeholder: "Add a tag",
					onChange: (event) => setTag(event.target.value)
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
					onClick: () => {
						const next = tag.trim();
						if (!next || desk.card.tags.includes(next)) return;
						patchCard({ tags: [...desk.card.tags, next].slice(0, 12) });
						setTag("");
					},
					children: "Add"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
					onClick: () => patchCard({ tags: [] }),
					children: "Remove all"
				})
			]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Aliases", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: desk.card.aliases,
				onChange: (event) => patchCard({ aliases: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Creator notes", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.card.creator_notes,
				onChange: (event) => patchCard({ creator_notes: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => {
				const parts = desk.card.description.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
				patchCard({
					personality: desk.card.personality || parts[1] || desk.card.personality,
					backstory: desk.card.backstory || parts[2] || desk.card.backstory,
					appearance: desk.card.appearance || parts[3] || desk.card.appearance
				});
				patch({ status: parts.length > 1 ? "Split the description into the empty fields." : "The description needs blank lines between sections." });
			},
			children: "Split description into fields"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: desk.personaMode,
				onChange: (event) => patch({ personaMode: event.target.checked })
			}), "This card stands for the human (persona)"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "display mt-6 text-xl",
			children: "Version history"
		}),
		desk.versions.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-2 text-sm text-[var(--muted)]",
			children: "No snapshots yet. Snapshot stores the version label from the header."
		}) : null,
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
			className: "mt-2 space-y-2",
			children: desk.versions.map((snap) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
				className: "flex flex-wrap items-center gap-2 rounded-md border border-[var(--line)] px-3 py-2 text-sm",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: snap.version }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-[var(--muted)]",
						children: snap.note
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-xs text-[var(--muted)]",
						children: snap.at
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "min-h-11 px-2",
						onClick: () => patchCard({ character_version: snap.version }),
						children: "Restore label"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "min-h-11 px-2 text-[var(--muted)]",
						onClick: () => patch({ versions: desk.versions.filter((item) => item.id !== snap.id) }),
						children: "Delete"
					})
				]
			}, snap.id))
		}),
		desk.versions.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => patch({
				versions: [],
				status: "Cleared version history."
			}),
			children: "Reset history"
		}) : null
	] });
}
function Lore({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => patch({ lore: [...desk.lore, {
				id: crypto.randomUUID(),
				keys: "",
				content: "",
				enabled: true
			}] }),
			children: "Add lore entry"
		}),
		desk.lore.map((entry) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-3 rounded-md border border-[var(--line)] p-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Keys", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: entry.keys,
						onChange: (event) => patch({ lore: desk.lore.map((item) => item.id === entry.id ? {
							...item,
							keys: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Content", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
						value: entry.content,
						onChange: (event) => patch({ lore: desk.lore.map((item) => item.id === entry.id ? {
							...item,
							content: event.target.value
						} : item) })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "mt-2 flex min-h-11 items-center gap-2 text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						type: "checkbox",
						checked: entry.enabled,
						onChange: (event) => patch({ lore: desk.lore.map((item) => item.id === entry.id ? {
							...item,
							enabled: event.target.checked
						} : item) })
					}), "Enabled"]
				})
			]
		}, entry.id)),
		desk.lore.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-3 text-sm text-[var(--muted)]",
			children: "No lore yet. Entries export inside the card’s character book."
		}) : null
	] });
}
function Gallery({ desk, onFile }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "mt-3 flex min-h-24 cursor-pointer items-center justify-center rounded-md border border-dashed border-[var(--line)] text-sm text-[var(--muted)]",
		children: ["Upload character images", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			type: "file",
			accept: "image/*",
			className: "sr-only",
			onChange: (event) => onFile(event.target.files?.[0])
		})]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
		className: "mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4",
		children: desk.gallery.map((src) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("img", {
			src,
			alt: "",
			className: "aspect-square w-full rounded-md object-cover"
		}) }, src.slice(0, 48)))
	})] });
}
function Colors({ desk, patch }) {
	const look = desk.look;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-3 sm:grid-cols-2",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Dialogue color", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					value: look.dialogue,
					onChange: (event) => patch({ look: {
						...look,
						dialogue: event.target.value
					} })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Name color", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					value: look.nameColor,
					onChange: (event) => patch({ look: {
						...look,
						nameColor: event.target.value
					} })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Message box color", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					value: look.messageBox,
					onChange: (event) => patch({ look: {
						...look,
						messageBox: event.target.value
					} })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Chat text size", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					type: "number",
					min: 12,
					max: 22,
					value: look.textSize,
					onChange: (event) => patch({ look: {
						...look,
						textSize: Number(event.target.value)
					} })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "mt-6 flex min-h-11 items-center gap-2 text-sm",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					type: "checkbox",
					checked: look.boldDialogue,
					onChange: (event) => patch({ look: {
						...look,
						boldDialogue: event.target.checked
					} })
				}), "Bold dialogue"]
			})
		]
	});
}
function Voice({ desk, patch }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "field",
		children: ["Voice", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			value: desk.voice,
			onChange: (event) => patch({ voice: event.target.value }),
			placeholder: "A voice name or file"
		})]
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "field",
		children: ["Phonetic name", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			value: desk.phonetic,
			onChange: (event) => patch({ phonetic: event.target.value })
		})]
	})] });
}
function StatsPanel({ desk, patch }) {
	const bars = desk.personaMode ? desk.personaBars : desk.pools;
	const key = desk.personaMode ? "personaBars" : "pools";
	function setBars(next) {
		patch({ [key]: next });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: desk.rpg,
				onChange: (event) => patch({ rpg: event.target.checked })
			}), "Enable RPG stats"]
		}),
		desk.rpg ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "display mt-4 text-xl",
				children: desk.personaMode ? "Status bars" : "Pools"
			}),
			bars.map((pool) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-2 grid gap-2 sm:grid-cols-4",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "box",
						value: pool.name,
						onChange: (event) => setBars(bars.map((item) => item.id === pool.id ? {
							...item,
							name: event.target.value
						} : item))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "box",
						type: "number",
						value: pool.current,
						onChange: (event) => setBars(bars.map((item) => item.id === pool.id ? {
							...item,
							current: Number(event.target.value)
						} : item))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "box",
						type: "number",
						value: pool.max,
						onChange: (event) => setBars(bars.map((item) => item.id === pool.id ? {
							...item,
							max: Number(event.target.value)
						} : item))
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "min-h-11 text-sm text-[var(--muted)]",
						onClick: () => setBars(bars.filter((item) => item.id !== pool.id)),
						children: "Remove"
					})
				]
			}, pool.id)),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => setBars([...bars, {
					id: crypto.randomUUID(),
					name: "Pool",
					current: 100,
					max: 100,
					color: "#e23d2b"
				}]),
				children: "Add pool"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "display mt-6 text-xl",
				children: "Attributes"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "mt-2 grid gap-2 sm:grid-cols-3",
				children: desk.attrs.map((attr) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "box",
						value: attr.name,
						onChange: (event) => patch({ attrs: desk.attrs.map((item) => item.id === attr.id ? {
							...item,
							name: event.target.value
						} : item) })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						className: "box",
						type: "number",
						value: attr.value,
						onChange: (event) => patch({ attrs: desk.attrs.map((item) => item.id === attr.id ? {
							...item,
							value: Number(event.target.value)
						} : item) })
					})]
				}, attr.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => patch({ attrs: [...desk.attrs, {
					id: crypto.randomUUID(),
					name: "NEW",
					value: 10
				}] }),
				children: "Add attribute"
			})
		] }) : null,
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Note", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.stats.note,
				onChange: (event) => patch({ stats: {
					...desk.stats,
					note: event.target.value
				} })
			})]
		})
	] });
}
function Advanced({ desk, patch, patchCard }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["System prompt", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.card.system_prompt,
				onChange: (event) => patchCard({ system_prompt: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Post-history instructions", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.card.post_history_instructions,
				onChange: (event) => patchCard({ post_history_instructions: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Depth prompt", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.depthPrompt,
				onChange: (event) => patch({ depthPrompt: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Depth", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					type: "number",
					min: 0,
					max: 12,
					value: desk.depth,
					onChange: (event) => patch({ depth: Number(event.target.value) })
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Role", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
					className: "box",
					value: desk.depthRole,
					onChange: (event) => patch({ depthRole: event.target.value }),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "system",
							children: "System"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "user",
							children: "User"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "assistant",
							children: "Assistant"
						})
					]
				})]
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Long memory", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: desk.card.long_memory,
				onChange: (event) => patchCard({ long_memory: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-3 grid gap-3 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["NovelAI token", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					type: "password",
					value: desk.novelToken,
					onChange: (event) => patch({ novelToken: event.target.value })
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["NovelAI model", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					value: desk.novelModel,
					onChange: (event) => patch({ novelModel: event.target.value })
				})]
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "display mt-6 text-xl",
			children: "Regex scripts"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "Find-and-replace rules applied to chat text before it is shown."
		}),
		desk.regex.map((script) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 grid gap-2 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box",
				value: script.find,
				placeholder: "Find",
				onChange: (event) => patch({ regex: desk.regex.map((item) => item.id === script.id ? {
					...item,
					find: event.target.value
				} : item) })
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box",
				value: script.replace,
				placeholder: "Replace",
				onChange: (event) => patch({ regex: desk.regex.map((item) => item.id === script.id ? {
					...item,
					replace: event.target.value
				} : item) })
			})]
		}, script.id)),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => patch({ regex: [...desk.regex, {
				id: crypto.randomUUID(),
				find: "",
				replace: "",
				enabled: true
			}] }),
			children: "Add script"
		})
	] });
}
function Chat({ desk, patch, busy, setBusy }) {
	const [draft, setDraft] = (0, import_react.useState)("");
	const preset = desk.presets.find((item) => item.id === desk.activePreset) ?? desk.presets[0];
	function show(text) {
		return desk.regex.filter((script) => script.enabled && script.find).reduce((line, script) => line.split(script.find).join(script.replace), text);
	}
	async function send() {
		const text = draft.trim();
		if (!text) return;
		const next = [...desk.chat, {
			id: crypto.randomUUID(),
			role: "user",
			text
		}];
		patch({ chat: next });
		setDraft("");
		setBusy(true);
		const lore = desk.lore.filter((entry) => entry.enabled && entry.content).filter((entry) => {
			const keys = entry.keys.split(",").map((key) => key.trim().toLowerCase()).filter(Boolean);
			return keys.length === 0 || keys.some((key) => text.toLowerCase().includes(key));
		}).map((entry) => entry.content).join("\n");
		const system = [
			desk.card.system_prompt,
			desk.convo.instruct,
			desk.card.name ? `You are ${desk.card.name}.` : "",
			desk.card.personality,
			desk.card.description,
			desk.card.scenario,
			desk.memory ? `Memory: ${desk.memory}` : "",
			lore ? `Lore:\n${lore}` : "",
			desk.card.post_history_instructions
		].filter(Boolean).join("\n\n");
		try {
			const reply = await chatReply(desk.kobold, desk.koboldKey, system || "Reply in character.", next, {
				temperature: preset?.temperature ?? desk.convo.temperature,
				maxTokens: Math.min(preset?.maxTokens ?? desk.convo.maxTokens, desk.convo.maxTokens || 420),
				topP: preset?.topP ?? desk.convo.topP
			});
			patch({
				chat: [...next, {
					id: crypto.randomUUID(),
					role: "assistant",
					text: reply.trim()
				}],
				status: "Replied."
			});
		} catch (error) {
			patch({ status: error instanceof Error ? error.message : "Could not reach KoboldCPP." });
		} finally {
			setBusy(false);
		}
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane mx-auto max-w-3xl",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: desk.card.name || "No character yet"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "text-sm text-[var(--muted)]",
				children: [
					desk.convo.name,
					" · ",
					preset?.name ?? "Preset"
				]
			}),
			desk.card.first_mes && desk.chat.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-3 rounded-md border border-[var(--line)] px-3 py-2 text-sm",
				style: {
					background: desk.look.messageBox,
					color: desk.look.dialogue
				},
				children: desk.card.first_mes
			}) : null,
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
				className: "field",
				children: ["Chat memory", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
					value: desk.memory,
					onChange: (event) => patch({ memory: event.target.value })
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "mt-4 space-y-3",
				children: desk.chat.map((line) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "rounded-md px-3 py-2 text-sm",
					style: {
						fontSize: desk.look.textSize,
						background: line.role === "assistant" ? desk.look.messageBox : void 0
					},
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", {
						style: { color: desk.look.nameColor },
						children: line.role === "user" ? "You" : desk.card.name || "Character"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: desk.look.boldDialogue && line.role === "assistant" ? "font-semibold" : "",
						style: { color: line.role === "assistant" ? desk.look.dialogue : void 0 },
						children: show(line.text)
					})]
				}, line.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mt-3 flex gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
					className: "box",
					value: draft,
					onChange: (event) => setDraft(event.target.value),
					placeholder: "Say something",
					onKeyDown: (event) => event.key === "Enter" && void send()
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					disabled: busy,
					onClick: () => void send(),
					className: "min-h-11 rounded-md bg-[var(--accent)] px-4 text-sm font-semibold text-[var(--accent-ink)]",
					children: "Send"
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-2 text-sm text-[var(--muted)]",
				children: desk.status
			})
		]
	});
}
function Generate({ desk, patch, cardPrompt }) {
	const gen = desk.generate;
	function set(partial) {
		patch({ generate: {
			...gen,
			...partial
		} });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "display text-2xl",
			children: "Generate"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "These are the RedGen controls. The AMD model runs in the Windows app; this desk keeps the same settings."
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Prompt", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: gen.prompt,
				onChange: (event) => set({ prompt: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => set({ prompt: desk.imageOverride && desk.imageTags.trim() ? desk.imageTags : cardPrompt }),
			children: "Use the card appearance"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Negative prompt", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: gen.negative,
				onChange: (event) => set({ negative: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 flex flex-wrap gap-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box max-w-xs",
				value: gen.promptName,
				placeholder: "Save prompt as",
				onChange: (event) => set({ promptName: event.target.value })
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
				type: "button",
				className: "min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
				onClick: () => {
					if (!gen.promptName.trim()) return;
					set({ savedPrompts: [...gen.savedPrompts, {
						name: gen.promptName.trim(),
						prompt: gen.prompt,
						negative: gen.negative
					}] });
				},
				children: "Save"
			})]
		}),
		gen.savedPrompts.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Saved prompts", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
				className: "box",
				onChange: (event) => {
					const found = gen.savedPrompts.find((item) => item.name === event.target.value);
					if (found) set({
						prompt: found.prompt,
						negative: found.negative,
						promptName: found.name
					});
				},
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
					value: "",
					children: "Choose"
				}), gen.savedPrompts.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", { children: item.name }, item.name))]
			})]
		}),
		gen.savedPrompts.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => set({ savedPrompts: gen.savedPrompts.filter((item) => item.name !== gen.promptName) }),
			children: "Delete saved prompt"
		}) : null,
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Steps",
					value: gen.steps,
					onChange: (steps) => set({ steps })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "CFG",
					value: gen.cfg,
					onChange: (cfg) => set({ cfg })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Batch count",
					value: gen.batch,
					onChange: (batch) => set({ batch })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Width",
					value: gen.width,
					onChange: (width) => set({ width })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Height",
					value: gen.height,
					onChange: (height) => set({ height })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Seed, blank is random", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: gen.seed,
						onChange: (event) => set({ seed: event.target.value })
					})]
				})
			]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Model", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.model,
				onChange: (event) => set({ model: event.target.value }),
				placeholder: "checkpoint path or name"
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Extra models, one per line", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: gen.models,
				onChange: (event) => set({ models: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["CLIP", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.clip,
				onChange: (event) => set({ clip: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["CLIP-G, SDXL only", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.clipG,
				onChange: (event) => set({ clipG: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["VAE", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.vae,
				onChange: (event) => set({ vae: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: gen.tile,
				onChange: (event) => set({ tile: event.target.checked })
			}), "Tile the VAE"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
				label: "Tile",
				value: gen.tileSize,
				onChange: (tileSize) => set({ tileSize })
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
				label: "Overlap",
				value: gen.tileOverlap,
				onChange: (tileOverlap) => set({ tileOverlap })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: gen.eyes,
				onChange: (event) => set({ eyes: event.target.checked })
			}), "Redraw eyes"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Eye detector file", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.eyeFile,
				onChange: (event) => set({ eyeFile: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-2",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
				label: "Denoise",
				value: gen.eyeDenoise,
				onChange: (eyeDenoise) => set({ eyeDenoise })
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
				label: "Confidence",
				value: gen.eyeConfidence,
				onChange: (eyeConfidence) => set({ eyeConfidence })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Eye prompt", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.eyePrompt,
				onChange: (event) => set({ eyePrompt: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-4 text-sm",
			children: "LoRAs"
		}),
		gen.loras.map((lora, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mt-2 grid gap-2 sm:grid-cols-[1fr_6rem]",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box",
				value: lora.path,
				placeholder: "LoRA file",
				onChange: (event) => set({ loras: gen.loras.map((item, i) => i === index ? {
					...item,
					path: event.target.value
				} : item) })
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box",
				type: "number",
				value: lora.weight,
				onChange: (event) => set({ loras: gen.loras.map((item, i) => i === index ? {
					...item,
					weight: Number(event.target.value)
				} : item) })
			})]
		}, index)),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
			type: "button",
			className: "mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm",
			onClick: () => set({ loras: [...gen.loras, {
				path: "",
				weight: 1
			}] }),
			children: "Add LoRA"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Image save location", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: gen.output,
				onChange: (event) => set({ output: event.target.value })
			})]
		})
	] });
}
function Captions({ desk, patch }) {
	const cap = desk.captions;
	function set(partial) {
		patch({ captions: {
			...cap,
			...partial
		} });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "display text-2xl",
			children: "Captions"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Caption with", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
				className: "box",
				value: cap.engine,
				onChange: (event) => set({ engine: event.target.value }),
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "kobold",
						children: "KoboldAI"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "clip",
						children: "CLIP Vision"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "joy",
						children: "JoyCaption Beta One"
					})
				]
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["What the pictures are", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
				className: "box",
				value: cap.kind,
				onChange: (event) => set({ kind: event.target.value }),
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "character",
						children: "Character"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "style",
						children: "Style"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "concept",
						children: "Concept"
					})
				]
			})]
		}),
		cap.engine === "kobold" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-2 text-sm text-[var(--muted)]",
			children: "Uses the Kobold address on the Card tab."
		}),
		cap.engine === "clip" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["CLIP Vision file", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.vision,
				onChange: (event) => set({ vision: event.target.value })
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Matching CLIP text file", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.visionText,
				onChange: (event) => set({ visionText: event.target.value })
			})]
		})] }),
		cap.engine === "joy" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["JoyCaption GGUF", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.joy,
				onChange: (event) => set({ joy: event.target.value })
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["mmproj", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.mmproj,
				onChange: (event) => set({ mmproj: event.target.value })
			})]
		})] }),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["What to ask", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: cap.ask,
				onChange: (event) => set({ ask: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Trigger word", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.trigger,
				onChange: (event) => set({ trigger: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Pictures, one path per line", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("textarea", {
				value: cap.files,
				onChange: (event) => set({ files: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Training folder", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: cap.folder,
				onChange: (event) => set({ folder: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-3 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: cap.copyPictures,
				onChange: (event) => set({ copyPictures: event.target.checked })
			}), "Copy pictures into the folder"]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: cap.skipExisting,
				onChange: (event) => set({ skipExisting: event.target.checked })
			}), "Skip pictures that already have a caption"]
		})
	] });
}
function Train({ desk, patch }) {
	const train = desk.train;
	const hints = {
		character: "A person. The trigger word is their name. Rank 32, alpha 16.",
		style: "A look. The trigger word is the style name. Rank 16, alpha 16.",
		concept: "An object or idea. The trigger word is the concept. Rank 16, alpha 8."
	};
	function set(partial) {
		patch({ train: {
			...train,
			...partial
		} });
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "display text-2xl",
			children: "Train a LoRA"
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "text-sm text-[var(--muted)]",
			children: "Uses the model selected on Generate. A matching .txt file captions each picture."
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["What you are training", /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
				className: "box",
				value: train.subject,
				onChange: (event) => {
					const subject = event.target.value;
					set({
						subject,
						...subject === "character" ? {
							rank: 32,
							alpha: 16
						} : subject === "style" ? {
							rank: 16,
							alpha: 16
						} : {
							rank: 16,
							alpha: 8
						}
					});
				},
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "character",
						children: "Character / likeness"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "style",
						children: "A specific style"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
						value: "concept",
						children: "A concept"
					})
				]
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "mt-2 text-sm text-[var(--muted)]",
			children: hints[train.subject]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "field",
			children: ["Image folder", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				value: train.folder,
				onChange: (event) => set({ folder: event.target.value })
			})]
		}),
		/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-3 sm:grid-cols-3",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Trigger word", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: train.trigger,
						onChange: (event) => set({ trigger: event.target.value })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["LoRA name", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: train.name,
						onChange: (event) => set({ name: event.target.value })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Network rank",
					value: train.rank,
					onChange: (rank) => set({ rank })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Network alpha",
					value: train.alpha,
					onChange: (alpha) => set({ alpha })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
					className: "field",
					children: ["Learning rate", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
						value: train.lr,
						onChange: (event) => set({ lr: event.target.value })
					})]
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Steps",
					value: train.steps,
					onChange: (steps) => set({ steps })
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					label: "Resolution",
					value: train.resolution,
					onChange: (resolution) => set({ resolution })
				})
			]
		}),
		[
			["buckets", "Aspect-ratio buckets"],
			["checkpoint", "Gradient checkpointing"],
			["cache", "Cache latents"],
			["noHalf", "No half VAE"]
		].map(([key, label]) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
			className: "mt-2 flex min-h-11 items-center gap-2 text-sm",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				type: "checkbox",
				checked: train[key],
				onChange: (event) => set({ [key]: event.target.checked })
			}), label]
		}, key))
	] });
}
function Library({ desk, patch }) {
	const [query, setQuery] = (0, import_react.useState)("");
	const cards = desk.library.filter((row) => `${row.card.name} ${row.title} ${row.card.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase()));
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "pane",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "display text-2xl",
				children: "Library"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				className: "box mt-3 max-w-md",
				value: query,
				placeholder: "Search characters/tags",
				onChange: (event) => setQuery(event.target.value)
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3",
				children: cards.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
					className: "rounded-md border border-[var(--line)] bg-[var(--surface)] p-3",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						type: "button",
						className: "w-full text-left",
						onClick: () => patch({
							card: row.card,
							title: row.title,
							favorite: row.favorite,
							portrait: row.portrait,
							concept: row.concept ?? "",
							openCardId: row.id,
							greetings: row.card.alternate_greetings.join("\n---\n"),
							mode: "characters",
							editorTab: "card"
						}),
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("strong", { children: row.card.name || "Unnamed" }),
							row.favorite ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "ml-2 text-[var(--red)]",
								children: "★"
							}) : null,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-xs text-[var(--muted)]",
								children: row.title || row.card.creator
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "mt-1 line-clamp-2 text-sm",
								children: row.card.summary || row.card.description
							})
						]
					})
				}, row.id))
			}),
			cards.length === 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-4 text-sm text-[var(--muted)]",
				children: "Keep a card from the editor and it shows up here."
			}) : null,
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "display mt-8 text-xl",
				children: "Personas"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "mt-2 space-y-2",
				children: desk.personas.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					className: "min-h-11 text-sm",
					onClick: () => patch({
						card: row.card,
						title: row.title,
						concept: row.concept ?? "",
						openCardId: row.id,
						greetings: row.card.alternate_greetings.join("\n---\n"),
						mode: "personas",
						personaMode: true,
						editorTab: "card"
					}),
					children: row.card.name || "Unnamed persona"
				}) }, row.id))
			})
		]
	});
}
function Num({ label, value, onChange }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
		className: "field",
		children: [label, /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
			type: "number",
			value,
			onChange: (event) => onChange(Number(event.target.value))
		})]
	});
}
var SplitComponent = Studio;
//#endregion
export { SplitComponent as component };
