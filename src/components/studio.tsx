import { useEffect, useState } from "react";
import { chatReply, download, normalizeCard, packPng, picturePrompt, rewriteField, slug, writeCard, blankCard, type Card } from "@/lib/cards";
import { blankDesk, loadDesk, saveDesk, type Desk, type GenerateSettings, type Pool } from "@/lib/desk";
import { Convo, Life, Lorebooks, Novel, Onboarding, PictureLibrary, Presets, Sprites } from "@/components/extra-panels";
import { CardDesk, bump } from "@/components/card-desk";
import { ThemePanel } from "@/components/theme-panel";
import { applyTheme, loadTheme, saveTheme, type AppTheme } from "@/lib/theme";

const BUILD = "62";

function putCard(current: Desk, card: Card, fresh: boolean, status?: string): Desk {
  const persona = current.personaMode || current.mode === "personas";
  const id = !fresh && current.openCardId ? current.openCardId : crypto.randomUUID();
  if (persona) {
    const row = { id, card, title: current.title, concept: current.concept };
    return {
      ...current,
      card,
      openCardId: id,
      personas: [row, ...current.personas.filter((item) => item.id !== id)],
      status: status ?? current.status,
    };
  }
  const row = { id, card, title: current.title, favorite: current.favorite, portrait: current.portrait, concept: current.concept };
  return {
    ...current,
    card,
    openCardId: id,
    library: [row, ...current.library.filter((item) => item.id !== id)],
    status: status ?? current.status,
  };
}

const TOP = [
  ["characters", "Characters"],
  ["personas", "Personas"],
  ["chat", "Chat"],
  ["lorebooks", "Lorebooks"],
  ["pictures", "Pictures"],
  ["library", "Library"],
  ["life", "Life"],
  ["presets", "Presets"],
  ["novel", "NovelAI"],
  ["theme", "Theme"],
] as const;

const EDITOR = [
  ["metadata", "Metadata"],
  ["card", "Card"],
  ["onboarding", "Onboarding"],
  ["convo", "Convo"],
  ["lore", "Lorebook"],
  ["sprites", "Sprites"],
  ["gallery", "Gallery"],
  ["colors", "Colors"],
  ["voice", "Voice"],
  ["stats", "Stats"],
  ["advanced", "Advanced"],
] as const;

const PICTURES = [
  ["generate", "Generate"],
  ["library", "Library"],
  ["captions", "Captions"],
  ["train", "Train"],
] as const;

export function Studio() {
  const [desk, setDesk] = useState<Desk>(blankDesk);
  const [theme, setTheme] = useState<AppTheme>(() => loadTheme());
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    applyTheme(theme);
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    const loaded = loadDesk();
    if (!loaded.characterId) loaded.characterId = crypto.randomUUID();
    setDesk(loaded);
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) saveDesk(desk);
  }, [desk, ready]);

  function patch(partial: Partial<Desk>) {
    setDesk((current) => ({ ...current, ...partial }));
  }

  function patchCard(partial: Partial<Card>) {
    setDesk((current) => ({ ...current, card: { ...current.card, ...partial } }));
  }

  function note(status: string) {
    patch({ status });
  }

  function storeOpen() {
    setDesk((current) => {
      const card = current.card;
      if (!card.name.trim() && !card.summary.trim() && !card.description.trim()) return current;
      return putCard(current, card, false);
    });
  }

  function openSaved(row: { id: string; card: Card; title: string; favorite?: boolean; portrait?: string; concept?: string }) {
    patch({
      card: row.card,
      title: row.title,
      favorite: row.favorite ?? false,
      portrait: row.portrait ?? "",
      concept: row.concept ?? desk.concept,
      openCardId: row.id,
      greetings: row.card.alternate_greetings.join("\n---\n"),
      editorTab: "card",
      status: `Opened ${row.card.name || "the card"}.`,
    });
  }

  function removeSaved(id: string) {
    setDesk((current) => {
      const status = "Removed that card from the library.";
      if (current.personaMode || current.mode === "personas") {
        return {
          ...current,
          personas: current.personas.filter((item) => item.id !== id),
          openCardId: current.openCardId === id ? "" : current.openCardId,
          status,
        };
      }
      return {
        ...current,
        library: current.library.filter((item) => item.id !== id),
        openCardId: current.openCardId === id ? "" : current.openCardId,
        status,
      };
    });
  }

  async function write() {
    setBusy(true);
    const persona = desk.personaMode || desk.mode === "personas";
    note(persona ? "Writing the persona…" : "Writing the card…");
    try {
      let concept = desk.concept;
      if (desk.sendRefs && desk.references.length) {
        concept += `\n\n${desk.references.length} reference pictures belong to this character. The starred picture is the portrait. Match the appearance to it.`;
      }
      const written = await writeCard(desk.kobold, desk.koboldKey, concept, persona, {
        temperature: desk.writerTemp,
        maxTokens: desk.writerMax,
      });
      setDesk((current) => {
        const previous = current.card;
        const next = { ...written };
        if (current.fillEmpty) {
          for (const key of ["name", "summary", "description", "personality", "scenario", "first_mes", "mes_example", "creator_notes", "system_prompt", "post_history_instructions", "creator", "backstory", "appearance", "aliases", "long_memory"] as const) {
            if (previous[key].trim()) next[key] = previous[key];
          }
          if (previous.tags.some((tag) => tag.trim())) next.tags = previous.tags;
          if (previous.alternate_greetings.some((item) => item.trim())) next.alternate_greetings = previous.alternate_greetings;
        }
        const had = Boolean(previous.name.trim() || previous.summary.trim() || previous.description.trim());
        const versions = had
          ? [{ id: crypto.randomUUID(), version: previous.character_version || "1.0", at: new Date().toLocaleString(), note: previous.summary.slice(0, 80) || previous.name || "Saved copy", card: previous }, ...current.versions].slice(0, 20)
          : current.versions;
        if (had && !current.fillEmpty) next.character_version = bump(previous.character_version || "1.0");
        return putCard({ ...current, versions, greetings: next.alternate_greetings.join("\n---\n") }, next, !had, "Wrote the card and saved it to the library.");
      });
    } catch (error) {
      note(error instanceof Error ? error.message : "Could not write the card.");
    } finally {
      setBusy(false);
    }
  }

  async function rewrite(field: keyof Card, label: string) {
    setBusy(true);
    note(`Rewriting ${label}…`);
    try {
      const usedBox = String(desk.card[field] ?? "").trim().length > 0;
      const text = await rewriteField(desk.kobold, desk.koboldKey, field, desk.concept, desk.card, {
        temperature: desk.writerTemp,
        maxTokens: desk.writerMax,
      });
      const source = usedBox ? "the note in that box" : "the other fields";
      setDesk((current) => putCard(current, { ...current.card, [field]: text }, false, `Rewrote ${label} from ${source} and saved the card.`));
    } catch (error) {
      note(error instanceof Error ? error.message : "Could not rewrite that field.");
    } finally {
      setBusy(false);
    }
  }

  function importCard(file: File | undefined) {
    if (!file) return;
    file
      .text()
      .then((text) => {
        const card = normalizeCard(JSON.parse(text));
        patch({ card, greetings: card.alternate_greetings.join("\n---\n"), status: `Imported ${card.name || "the card"}.` });
      })
      .catch(() => note("That file is not a character card."));
  }

  function snapshot() {
    const version = desk.card.character_version || "1.0";
    patch({
      versions: [{ id: crypto.randomUUID(), version, at: new Date().toLocaleString(), note: desk.card.summary.slice(0, 80) || desk.card.name || "Snapshot" }, ...desk.versions].slice(0, 12),
      status: `Saved version ${version}.`,
    });
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
      status: "Started a new card.",
    });
  }

  async function copyJson() {
    const greetings = desk.greetings.split(/\n---\n/).map((item) => item.trim()).filter(Boolean);
    const card = { ...desk.card, alternate_greetings: desk.card.alternate_greetings.filter((item) => item.trim()) || greetings };
    try {
      await navigator.clipboard.writeText(JSON.stringify(v2(card, desk), null, 2));
      note("Copied the card JSON.");
    } catch {
      note("Could not copy the card.");
    }
  }
  function keepInLibrary() {
    const id = crypto.randomUUID();
    const row = { id, card: desk.card, title: desk.title, favorite: desk.favorite, portrait: desk.portrait, concept: desk.concept };
    if (desk.mode === "personas" || desk.personaMode) {
      patch({ personas: [{ id, card: desk.card, title: desk.title, concept: desk.concept }, ...desk.personas], openCardId: id, status: "Kept the persona." });
      return;
    }
    patch({ library: [row, ...desk.library], openCardId: id, status: "Kept the card in the library." });
  }

  async function saveJson() {
    const greetings = desk.greetings.split(/\n---\n/).map((item) => item.trim()).filter(Boolean);
    const card = {
      ...desk.card,
      tags: desk.card.tags.filter((tag) => tag.trim()),
      alternate_greetings: desk.card.alternate_greetings.filter((item) => item.trim()).length
        ? desk.card.alternate_greetings.filter((item) => item.trim())
        : greetings,
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

  function readImage(file: File | undefined, into: "portrait" | "gallery") {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result || "");
      if (into === "portrait") patch({ portrait: url, status: "Portrait attached." });
      else patch({ gallery: [url, ...desk.gallery], status: "Added to the gallery." });
    };
    reader.readAsDataURL(file);
  }

  const prompt = picturePrompt(desk.card);

  return (
    <div className="shell">
      <header className="topnav">
        <strong className="display text-xl">RedWright</strong>
        <span className="mr-2 text-xs text-[var(--muted)]">build {BUILD}</span>
        {TOP.map(([id, label]) => (
          <button key={id} type="button" onClick={() => patch({ mode: id })} className={`nav-btn ${desk.mode === id ? "on" : ""}`}>
            {label}
          </button>
        ))}
      </header>

      {desk.mode === "characters" || desk.mode === "personas" ? (
        <CardDesk
          desk={desk}
          patch={patch}
          patchCard={patchCard}
          busy={busy}
          onWrite={() => void write()}
          onRewrite={(field, label) => void rewrite(field, label)}
          onOpen={openSaved}
          onRemove={removeSaved}
          onKeep={keepInLibrary}
          onNew={newCard}
          onJson={() => void saveJson()}
          onPng={() => void savePng()}
          onCopy={() => void copyJson()}
          onImport={importCard}
          extras={
            <>
              <Onboarding desk={desk} patch={patch} />
              <Metadata desk={desk} patch={patch} patchCard={patchCard} />
              <Convo desk={desk} patch={patch} />
              <Lore desk={desk} patch={patch} />
              <Sprites desk={desk} patch={patch} />
              <Gallery desk={desk} onFile={(file) => readImage(file, "gallery")} />
              <Colors desk={desk} patch={patch} />
              <Voice desk={desk} patch={patch} />
              <StatsPanel desk={desk} patch={patch} />
              <Advanced desk={desk} patch={patch} patchCard={patchCard} />
            </>
          }
        />
      ) : null}

      {desk.mode === "theme" && (
        <div className="mode-scroll">
          <ThemePanel theme={theme} onChange={setTheme} />
        </div>
      )}

      {desk.mode === "chat" && <Chat desk={desk} patch={patch} busy={busy} setBusy={setBusy} />}
      {desk.mode === "lorebooks" && <Lorebooks desk={desk} patch={patch} />}
      {desk.mode === "life" && <Life desk={desk} patch={patch} />}
      {desk.mode === "presets" && <Presets desk={desk} patch={patch} />}
      {desk.mode === "novel" && <Novel desk={desk} patch={patch} />}
      {desk.mode === "pictures" && (
        <div className="work">
          <nav className="rail" aria-label="Picture tools">
            {PICTURES.map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => patch({ pictureTab: id })}
                className={`nav-btn ${desk.pictureTab === id ? "on" : ""}`}
              >
                {label}
              </button>
            ))}
          </nav>
          <section className="pane">
            {desk.pictureTab === "generate" && <Generate desk={desk} patch={patch} cardPrompt={prompt} />}
            {desk.pictureTab === "library" && <PictureLibrary desk={desk} patch={patch} />}
            {desk.pictureTab === "captions" && <Captions desk={desk} patch={patch} />}
            {desk.pictureTab === "train" && <Train desk={desk} patch={patch} />}
            <p className="mt-4 text-sm text-[var(--muted)]">{desk.status}</p>
          </section>
        </div>
      )}
      {desk.mode === "library" && <Library desk={desk} patch={patch} />}
    </div>
  );
}

function v2(card: Card, desk: Desk) {
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
        return entries.length
          ? {
              name: linked?.name || `${card.name || "Card"} lore`,
              entries: entries.map((entry, index) => ({
                id: index,
                keys: entry.keys.split(",").map((key) => key.trim()).filter(Boolean),
                content: entry.content,
                enabled: entry.enabled,
                insertion_order: index,
              })),
            }
          : null;
      })(),
      extensions: {
        talkativeness: card.talkativeness,
        fav: desk.favorite,
        backstory: card.backstory,
        appearance: card.appearance,
        aliases: card.aliases,
        long_memory: [card.long_memory, ...desk.life.map((beat) => [beat.when, beat.title, beat.body].filter(Boolean).join(" — "))].filter(Boolean).join("\n"),
        title: desk.title,
        chat_look: desk.look,
        voice: desk.voice,
        phonetic_name: desk.phonetic,
        stats: desk.stats,
        rpg: desk.rpg,
        pools: desk.pools,
        attributes: desk.attrs,
        persona_bars: desk.personaBars,
        depth_prompt: { prompt: desk.depthPrompt, depth: desk.depth, role: desk.depthRole },
        image_override: desk.imageOverride,
        image_tags: desk.imageTags,
        onboarding: desk.onboarding,
        convo: desk.convo,
        sprites: desk.sprites,
        sprite_layout: desk.spriteLayout,
        regex_scripts: desk.regex,
        character_id: desk.characterId,
      },
    },
  };
}

function EditorHead({
  desk,
  patch,
  patchCard,
  busy,
  onFile,
  onImport,
  onSnapshot,
  onGenerateName,
  onStore,
}: {
  desk: Desk;
  patch: (partial: Partial<Desk>) => void;
  patchCard: (partial: Partial<Card>) => void;
  busy: boolean;
  onFile: (file: File | undefined) => void;
  onImport: (file: File | undefined) => void;
  onSnapshot: () => void;
  onGenerateName: () => void;
  onStore: () => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 border-b border-[var(--line)] pb-4">
      <label className="grid h-20 w-16 cursor-pointer place-items-center overflow-hidden rounded-md border border-[var(--line)] bg-[var(--bg)] text-xs text-[var(--muted)]">
        {desk.portrait ? <img src={desk.portrait} alt="" className="h-full w-full object-cover" /> : "Avatar"}
        <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(event) => onFile(event.target.files?.[0])} />
      </label>
      <div className="field min-w-48 flex-1">
        <span className="flex items-center justify-between gap-2">
          Name
          <button type="button" disabled={busy} className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm text-[var(--fg)] disabled:opacity-60" onClick={onGenerateName}>
            Generate
          </button>
        </span>
        <input value={desk.card.name} onChange={(event) => patchCard({ name: event.target.value })} onBlur={onStore} />
      </div>
      <label className="field min-w-40 flex-1">
        Title
        <input value={desk.title} onChange={(event) => patch({ title: event.target.value })} placeholder="Modern AU version" />
      </label>
      <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patch({ favorite: !desk.favorite })}>
        {desk.favorite ? "Favorited" : "Favorite"}
      </button>
      <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={onSnapshot}>
        Snapshot
      </button>
      <label className="min-h-11 cursor-pointer rounded-md border border-[var(--line)] px-3 py-2 text-sm">
        Import
        <input type="file" accept="application/json,.json,.png" className="sr-only" onChange={(event) => onImport(event.target.files?.[0])} />
      </label>
      <p className="w-full text-xs text-[var(--muted)]">
        {desk.card.creator || "Cardwright"} · {desk.card.character_version || "1.0"} · {desk.characterId.slice(0, 8)}
      </p>
    </div>
  );
}

function Metadata({ desk, patch, patchCard }: { desk: Desk; patch: (p: Partial<Desk>) => void; patchCard: (p: Partial<Card>) => void }) {
  const [tag, setTag] = useState("");
  return (
    <div>
      <label className="field">
        Character ID
        <input readOnly value={desk.characterId} />
      </label>
      <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => void navigator.clipboard.writeText(desk.characterId)}>
        Copy ID
      </button>
      <label className="field">
        Creator
        <input value={desk.card.creator} onChange={(event) => patchCard({ creator: event.target.value })} />
      </label>
      <label className="field">
        Version
        <input value={desk.card.character_version} onChange={(event) => patchCard({ character_version: event.target.value })} />
      </label>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={desk.autoVersion} onChange={(event) => patch({ autoVersion: event.target.checked })} />
        Automatic versioning
      </label>
      <label className="field">
        Talkativeness {desk.card.talkativeness}
        <input type="range" min={0} max={100} value={desk.card.talkativeness} onChange={(event) => patchCard({ talkativeness: Number(event.target.value) })} />
      </label>
      <div className="mt-3 flex flex-wrap gap-2">
        {desk.card.tags.map((item) => (
          <button key={item} type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patchCard({ tags: desk.card.tags.filter((tagName) => tagName !== item) })}>
            {item} ×
          </button>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <input className="box max-w-xs" value={tag} placeholder="Add a tag" onChange={(event) => setTag(event.target.value)} />
        <button
          type="button"
          className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
          onClick={() => {
            const next = tag.trim();
            if (!next || desk.card.tags.includes(next)) return;
            patchCard({ tags: [...desk.card.tags, next].slice(0, 12) });
            setTag("");
          }}
        >
          Add
        </button>
        <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patchCard({ tags: [] })}>
          Remove all
        </button>
      </div>
      <label className="field">
        Aliases
        <input value={desk.card.aliases} onChange={(event) => patchCard({ aliases: event.target.value })} />
      </label>
      <label className="field">
        Creator notes
        <textarea value={desk.card.creator_notes} onChange={(event) => patchCard({ creator_notes: event.target.value })} />
      </label>
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() => {
          const parts = desk.card.description.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
          patchCard({
            personality: desk.card.personality || parts[1] || desk.card.personality,
            backstory: desk.card.backstory || parts[2] || desk.card.backstory,
            appearance: desk.card.appearance || parts[3] || desk.card.appearance,
          });
          patch({ status: parts.length > 1 ? "Split the description into the empty fields." : "The description needs blank lines between sections." });
        }}
      >
        Split description into fields
      </button>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={desk.personaMode} onChange={(event) => patch({ personaMode: event.target.checked })} />
        This card stands for the human (persona)
      </label>
      <h3 className="display mt-6 text-xl">Version history</h3>
      {desk.versions.length === 0 ? <p className="mt-2 text-sm text-[var(--muted)]">No snapshots yet. Snapshot stores the version label from the header.</p> : null}
      <ul className="mt-2 space-y-2">
        {desk.versions.map((snap) => (
          <li key={snap.id} className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--line)] px-3 py-2 text-sm">
            <span>{snap.version}</span>
            <span className="text-[var(--muted)]">{snap.note}</span>
            <span className="text-xs text-[var(--muted)]">{snap.at}</span>
            <button type="button" className="min-h-11 px-2" onClick={() => patchCard({ character_version: snap.version })}>
              Restore label
            </button>
            <button type="button" className="min-h-11 px-2 text-[var(--muted)]" onClick={() => patch({ versions: desk.versions.filter((item) => item.id !== snap.id) })}>
              Delete
            </button>
          </li>
        ))}
      </ul>
      {desk.versions.length > 0 ? (
        <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patch({ versions: [], status: "Cleared version history." })}>
          Reset history
        </button>
      ) : null}
    </div>
  );
}

function CardFields({
  desk,
  patch,
  patchCard,
  busy,
  onWrite,
  onGenerate,
  onOpen,
  onRemove,
  onStore,
}: {
  desk: Desk;
  patch: (p: Partial<Desk>) => void;
  patchCard: (p: Partial<Card>) => void;
  busy: boolean;
  onWrite: () => void;
  onGenerate: (field: keyof Card, label: string) => void;
  onOpen: (row: { id: string; card: Card; title: string; favorite?: boolean; portrait?: string; concept?: string }) => void;
  onRemove: (id: string) => void;
  onStore: () => void;
}) {
  const rows: [keyof Card, string][] = [
    ["summary", "Summary"],
    ["description", "Description"],
    ["personality", "Personality"],
    ["backstory", "Backstory"],
    ["appearance", "Appearance"],
    ["scenario", "Scenario"],
    ["first_mes", "First message"],
    ["mes_example", "Example dialogue"],
  ];
  const greetings = desk.greetings.length ? desk.greetings.split(/\n---\n/) : [];
  const saved = desk.personaMode || desk.mode === "personas" ? desk.personas : desk.library;
  function setGreetings(next: string[]) {
    patch({ greetings: next.join("\n---\n") });
  }
  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="rounded-md border border-[var(--line)] p-3">
        <h3 className="display text-lg">Card library</h3>
        <p className="text-xs text-[var(--muted)]">Every card you write is kept here.</p>
        <ul className="mt-2 max-h-80 space-y-1 overflow-auto">
          {saved.map((row) => (
            <li key={row.id} className="flex items-center gap-1">
              <button
                type="button"
                className={`min-h-11 flex-1 rounded-md px-2 text-left text-sm ${desk.openCardId === row.id ? "bg-[var(--red)] font-semibold text-white" : ""}`}
                onClick={() => onOpen(row)}
              >
                {row.card.name || "Unnamed"}
              </button>
              <button type="button" className="min-h-11 px-2 text-sm text-[var(--muted)]" onClick={() => onRemove(row.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
        {saved.length === 0 ? <p className="mt-2 text-sm text-[var(--muted)]">Nothing saved yet.</p> : null}
      </aside>
      <div>
      <div className="flex gap-2 overflow-x-auto text-sm">
        {rows.map(([key, label]) => (
          <a key={key} href={`#field-${key}`} className="shrink-0 text-[var(--muted)] underline-offset-2 hover:underline">
            {label}
          </a>
        ))}
      </div>
      <label className="field">
        Concept for Kobold
        <textarea value={desk.concept} onChange={(event) => patch({ concept: event.target.value })} />
      </label>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="field">
          Kobold address
          <input value={desk.kobold} onChange={(event) => patch({ kobold: event.target.value })} />
        </label>
        <label className="field">
          API key
          <input type="password" value={desk.koboldKey} onChange={(event) => patch({ koboldKey: event.target.value })} />
        </label>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" disabled={busy} onClick={onWrite} className="min-h-11 rounded-md bg-[var(--red)] px-4 text-sm font-semibold text-white disabled:opacity-60">
          {desk.personaMode ? "Write persona" : "Write card"}
        </button>
      </div>
      {rows.map(([key, label]) => (
        <div key={key} id={`field-${key}`}>
          <div className="mt-3 flex items-center justify-between gap-2 text-xs text-[var(--muted)]">
            <span>
              {label} · {String(desk.card[key] ?? "").length}
            </span>
            <button type="button" disabled={busy} className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm text-[var(--fg)] disabled:opacity-60" onClick={() => onGenerate(key, label)}>
              Generate
            </button>
          </div>
          <textarea className="box" value={String(desk.card[key] ?? "")} onChange={(event) => patchCard({ [key]: event.target.value })} onBlur={onStore} />
        </div>
      ))}
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={desk.imageOverride} onChange={(event) => patch({ imageOverride: event.target.checked })} />
        Image appearance override
      </label>
      {desk.imageOverride ? (
        <label className="field">
          Image tags, used instead of a rewritten appearance
          <textarea value={desk.imageTags} onChange={(event) => patch({ imageTags: event.target.value })} />
        </label>
      ) : null}
      <div className="mt-4 flex items-center justify-between">
        <h3 className="display text-xl">Alternate greetings</h3>
        <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => setGreetings([...greetings, ""])}>
          Add greeting
        </button>
      </div>
      {greetings.map((greeting, index) => (
        <div key={index} className="mt-2">
          <div className="flex gap-2">
            <button type="button" className="min-h-11 px-2 text-sm" onClick={() => index > 0 && setGreetings(move(greetings, index, index - 1))}>
              Up
            </button>
            <button type="button" className="min-h-11 px-2 text-sm" onClick={() => index < greetings.length - 1 && setGreetings(move(greetings, index, index + 1))}>
              Down
            </button>
            <button type="button" className="min-h-11 px-2 text-sm text-[var(--muted)]" onClick={() => setGreetings(greetings.filter((_, item) => item !== index))}>
              Remove
            </button>
          </div>
          <textarea className="box" value={greeting} onChange={(event) => setGreetings(greetings.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))} />
        </div>
      ))}
      </div>
    </div>
  );
}

function move<T>(list: T[], from: number, to: number): T[] {
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

function Lore({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  return (
    <div>
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() => patch({ lore: [...desk.lore, { id: crypto.randomUUID(), keys: "", content: "", enabled: true }] })}
      >
        Add lore entry
      </button>
      {desk.lore.map((entry) => (
        <div key={entry.id} className="mt-3 rounded-md border border-[var(--line)] p-3">
          <label className="field">
            Keys
            <input
              value={entry.keys}
              onChange={(event) => patch({ lore: desk.lore.map((item) => (item.id === entry.id ? { ...item, keys: event.target.value } : item)) })}
            />
          </label>
          <label className="field">
            Content
            <textarea
              value={entry.content}
              onChange={(event) => patch({ lore: desk.lore.map((item) => (item.id === entry.id ? { ...item, content: event.target.value } : item)) })}
            />
          </label>
          <label className="mt-2 flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={entry.enabled}
              onChange={(event) => patch({ lore: desk.lore.map((item) => (item.id === entry.id ? { ...item, enabled: event.target.checked } : item)) })}
            />
            Enabled
          </label>
        </div>
      ))}
      {desk.lore.length === 0 ? <p className="mt-3 text-sm text-[var(--muted)]">No lore yet. Entries export inside the card’s character book.</p> : null}
    </div>
  );
}

function Gallery({ desk, onFile }: { desk: Desk; onFile: (file: File | undefined) => void }) {
  return (
    <div>
      <label className="mt-3 flex min-h-24 cursor-pointer items-center justify-center rounded-md border border-dashed border-[var(--line)] text-sm text-[var(--muted)]">
        Upload character images
        <input type="file" accept="image/*" className="sr-only" onChange={(event) => onFile(event.target.files?.[0])} />
      </label>
      <ul className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
        {desk.gallery.map((src) => (
          <li key={src.slice(0, 48)}>
            <img src={src} alt="" className="aspect-square w-full rounded-md object-cover" />
          </li>
        ))}
      </ul>
    </div>
  );
}

function Colors({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  const look = desk.look;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="field">
        Dialogue color
        <input value={look.dialogue} onChange={(event) => patch({ look: { ...look, dialogue: event.target.value } })} />
      </label>
      <label className="field">
        Name color
        <input value={look.nameColor} onChange={(event) => patch({ look: { ...look, nameColor: event.target.value } })} />
      </label>
      <label className="field">
        Message box color
        <input value={look.messageBox} onChange={(event) => patch({ look: { ...look, messageBox: event.target.value } })} />
      </label>
      <label className="field">
        Chat text size
        <input type="number" min={12} max={22} value={look.textSize} onChange={(event) => patch({ look: { ...look, textSize: Number(event.target.value) } })} />
      </label>
      <label className="mt-6 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={look.boldDialogue} onChange={(event) => patch({ look: { ...look, boldDialogue: event.target.checked } })} />
        Bold dialogue
      </label>
    </div>
  );
}

function Voice({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  return (
    <div>
      <label className="field">
        Voice
        <input value={desk.voice} onChange={(event) => patch({ voice: event.target.value })} placeholder="A voice name or file" />
      </label>
      <label className="field">
        Phonetic name
        <input value={desk.phonetic} onChange={(event) => patch({ phonetic: event.target.value })} />
      </label>
    </div>
  );
}

function StatsPanel({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  const bars = desk.personaMode ? desk.personaBars : desk.pools;
  const key = desk.personaMode ? "personaBars" : "pools";
  function setBars(next: Pool[]) {
    patch({ [key]: next });
  }
  return (
    <div>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={desk.rpg} onChange={(event) => patch({ rpg: event.target.checked })} />
        Enable RPG stats
      </label>
      {desk.rpg ? (
        <>
          <h3 className="display mt-4 text-xl">{desk.personaMode ? "Status bars" : "Pools"}</h3>
          {bars.map((pool) => (
            <div key={pool.id} className="mt-2 grid gap-2 sm:grid-cols-4">
              <input className="box" value={pool.name} onChange={(event) => setBars(bars.map((item) => (item.id === pool.id ? { ...item, name: event.target.value } : item)))} />
              <input className="box" type="number" value={pool.current} onChange={(event) => setBars(bars.map((item) => (item.id === pool.id ? { ...item, current: Number(event.target.value) } : item)))} />
              <input className="box" type="number" value={pool.max} onChange={(event) => setBars(bars.map((item) => (item.id === pool.id ? { ...item, max: Number(event.target.value) } : item)))} />
              <button type="button" className="min-h-11 text-sm text-[var(--muted)]" onClick={() => setBars(bars.filter((item) => item.id !== pool.id))}>
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
            onClick={() => setBars([...bars, { id: crypto.randomUUID(), name: "Pool", current: 100, max: 100, color: "#e23d2b" }])}
          >
            Add pool
          </button>
          <h3 className="display mt-6 text-xl">Attributes</h3>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {desk.attrs.map((attr) => (
              <label key={attr.id} className="field">
                <input className="box" value={attr.name} onChange={(event) => patch({ attrs: desk.attrs.map((item) => (item.id === attr.id ? { ...item, name: event.target.value } : item)) })} />
                <input className="box" type="number" value={attr.value} onChange={(event) => patch({ attrs: desk.attrs.map((item) => (item.id === attr.id ? { ...item, value: Number(event.target.value) } : item)) })} />
              </label>
            ))}
          </div>
          <button
            type="button"
            className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
            onClick={() => patch({ attrs: [...desk.attrs, { id: crypto.randomUUID(), name: "NEW", value: 10 }] })}
          >
            Add attribute
          </button>
        </>
      ) : null}
      <label className="field">
        Note
        <textarea value={desk.stats.note} onChange={(event) => patch({ stats: { ...desk.stats, note: event.target.value } })} />
      </label>
    </div>
  );
}

function Advanced({ desk, patch, patchCard }: { desk: Desk; patch: (p: Partial<Desk>) => void; patchCard: (p: Partial<Card>) => void }) {
  return (
    <div>
      <label className="field">
        System prompt
        <textarea value={desk.card.system_prompt} onChange={(event) => patchCard({ system_prompt: event.target.value })} />
      </label>
      <label className="field">
        Post-history instructions
        <textarea value={desk.card.post_history_instructions} onChange={(event) => patchCard({ post_history_instructions: event.target.value })} />
      </label>
      <label className="field">
        Depth prompt
        <textarea value={desk.depthPrompt} onChange={(event) => patch({ depthPrompt: event.target.value })} />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="field">
          Depth
          <input type="number" min={0} max={12} value={desk.depth} onChange={(event) => patch({ depth: Number(event.target.value) })} />
        </label>
        <label className="field">
          Role
          <select className="box" value={desk.depthRole} onChange={(event) => patch({ depthRole: event.target.value as Desk["depthRole"] })}>
            <option value="system">System</option>
            <option value="user">User</option>
            <option value="assistant">Assistant</option>
          </select>
        </label>
      </div>
      <label className="field">
        Long memory
        <textarea value={desk.card.long_memory} onChange={(event) => patchCard({ long_memory: event.target.value })} />
      </label>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="field">
          NovelAI token
          <input type="password" value={desk.novelToken} onChange={(event) => patch({ novelToken: event.target.value })} />
        </label>
        <label className="field">
          NovelAI model
          <input value={desk.novelModel} onChange={(event) => patch({ novelModel: event.target.value })} />
        </label>
      </div>
      <h3 className="display mt-6 text-xl">Regex scripts</h3>
      <p className="text-sm text-[var(--muted)]">Find-and-replace rules applied to chat text before it is shown.</p>
      {desk.regex.map((script) => (
        <div key={script.id} className="mt-2 grid gap-2 sm:grid-cols-2">
          <input className="box" value={script.find} placeholder="Find" onChange={(event) => patch({ regex: desk.regex.map((item) => (item.id === script.id ? { ...item, find: event.target.value } : item)) })} />
          <input className="box" value={script.replace} placeholder="Replace" onChange={(event) => patch({ regex: desk.regex.map((item) => (item.id === script.id ? { ...item, replace: event.target.value } : item)) })} />
        </div>
      ))}
      <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patch({ regex: [...desk.regex, { id: crypto.randomUUID(), find: "", replace: "", enabled: true }] })}>
        Add script
      </button>
    </div>
  );
}

function Actions({ busy, onKeep, onJson, onPng, status }: { busy: boolean; onKeep: () => void; onJson: () => void; onPng: () => void; status: string }) {
  return (
    <div className="mt-4 border-t border-[var(--line)] pt-3">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={onKeep} className="min-h-11 rounded-md bg-[var(--paper)] px-3 text-sm font-semibold text-[var(--ink)]">
          Keep
        </button>
        <button type="button" onClick={onJson} className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm">
          Export JSON
        </button>
        <button type="button" disabled={busy} onClick={onPng} className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm disabled:opacity-60">
          Export PNG
        </button>
      </div>
      <p className="mt-2 text-sm text-[var(--muted)]">{status}</p>
    </div>
  );
}

function Chat({ desk, patch, busy, setBusy }: { desk: Desk; patch: (p: Partial<Desk>) => void; busy: boolean; setBusy: (v: boolean) => void }) {
  const [draft, setDraft] = useState("");
  const preset = desk.presets.find((item) => item.id === desk.activePreset) ?? desk.presets[0];
  function show(text: string) {
    return desk.regex.filter((script) => script.enabled && script.find).reduce((line, script) => line.split(script.find).join(script.replace), text);
  }
  async function send() {
    const text = draft.trim();
    if (!text) return;
    const next = [...desk.chat, { id: crypto.randomUUID(), role: "user" as const, text }];
    patch({ chat: next });
    setDraft("");
    setBusy(true);
    const lore = desk.lore
      .filter((entry) => entry.enabled && entry.content)
      .filter((entry) => {
        const keys = entry.keys.split(",").map((key) => key.trim().toLowerCase()).filter(Boolean);
        return keys.length === 0 || keys.some((key) => text.toLowerCase().includes(key));
      })
      .map((entry) => entry.content)
      .join("\n");
    const system = [
      desk.card.system_prompt,
      desk.convo.instruct,
      desk.card.name ? `You are ${desk.card.name}.` : "",
      desk.card.personality,
      desk.card.description,
      desk.card.scenario,
      desk.memory ? `Memory: ${desk.memory}` : "",
      lore ? `Lore:\n${lore}` : "",
      desk.card.post_history_instructions,
    ]
      .filter(Boolean)
      .join("\n\n");
    try {
      const reply = await chatReply(desk.kobold, desk.koboldKey, system || "Reply in character.", next, {
        temperature: preset?.temperature ?? desk.convo.temperature,
        maxTokens: Math.min(preset?.maxTokens ?? desk.convo.maxTokens, desk.convo.maxTokens || 420),
        topP: preset?.topP ?? desk.convo.topP,
      });
      patch({ chat: [...next, { id: crypto.randomUUID(), role: "assistant", text: reply.trim() }], status: "Replied." });
    } catch (error) {
      patch({ status: error instanceof Error ? error.message : "Could not reach KoboldCPP." });
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="pane mx-auto max-w-3xl">
      <h2 className="display text-2xl">{desk.card.name || "No character yet"}</h2>
      <p className="text-sm text-[var(--muted)]">{desk.convo.name} · {preset?.name ?? "Preset"}</p>
      {desk.card.first_mes && desk.chat.length === 0 ? (
        <p className="mt-3 rounded-md border border-[var(--line)] px-3 py-2 text-sm" style={{ background: desk.look.messageBox, color: desk.look.dialogue }}>
          {desk.card.first_mes}
        </p>
      ) : null}
      <label className="field">
        Chat memory
        <textarea value={desk.memory} onChange={(event) => patch({ memory: event.target.value })} />
      </label>
      <ul className="mt-4 space-y-3">
        {desk.chat.map((line) => (
          <li key={line.id} className="rounded-md px-3 py-2 text-sm" style={{ fontSize: desk.look.textSize, background: line.role === "assistant" ? desk.look.messageBox : undefined }}>
            <strong style={{ color: desk.look.nameColor }}>{line.role === "user" ? "You" : desk.card.name || "Character"}</strong>
            <p className={desk.look.boldDialogue && line.role === "assistant" ? "font-semibold" : ""} style={{ color: line.role === "assistant" ? desk.look.dialogue : undefined }}>
              {show(line.text)}
            </p>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <input className="box" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Say something" onKeyDown={(event) => event.key === "Enter" && void send()} />
        <button type="button" disabled={busy} onClick={() => void send()} className="min-h-11 rounded-md bg-[var(--accent)] px-4 text-sm font-semibold text-[var(--accent-ink)]">
          Send
        </button>
      </div>
      <p className="mt-2 text-sm text-[var(--muted)]">{desk.status}</p>
    </section>
  );
}

function Generate({ desk, patch, cardPrompt }: { desk: Desk; patch: (p: Partial<Desk>) => void; cardPrompt: string }) {
  const gen = desk.generate;
  function set(partial: Partial<GenerateSettings>) {
    patch({ generate: { ...gen, ...partial } });
  }
  return (
    <div>
      <h2 className="display text-2xl">Generate</h2>
      <p className="text-sm text-[var(--muted)]">These are the RedGen controls. The AMD model runs in the Windows app; this desk keeps the same settings.</p>
      <label className="field">
        Prompt
        <textarea value={gen.prompt} onChange={(event) => set({ prompt: event.target.value })} />
      </label>
      <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => set({ prompt: desk.imageOverride && desk.imageTags.trim() ? desk.imageTags : cardPrompt })}>
        Use the card appearance
      </button>
      <label className="field">
        Negative prompt
        <textarea value={gen.negative} onChange={(event) => set({ negative: event.target.value })} />
      </label>
      <div className="mt-2 flex flex-wrap gap-2">
        <input className="box max-w-xs" value={gen.promptName} placeholder="Save prompt as" onChange={(event) => set({ promptName: event.target.value })} />
        <button
          type="button"
          className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
          onClick={() => {
            if (!gen.promptName.trim()) return;
            set({ savedPrompts: [...gen.savedPrompts, { name: gen.promptName.trim(), prompt: gen.prompt, negative: gen.negative }] });
          }}
        >
          Save
        </button>
      </div>
      {gen.savedPrompts.length > 0 && (
        <label className="field">
          Saved prompts
          <select
            className="box"
            onChange={(event) => {
              const found = gen.savedPrompts.find((item) => item.name === event.target.value);
              if (found) set({ prompt: found.prompt, negative: found.negative, promptName: found.name });
            }}
          >
            <option value="">Choose</option>
            {gen.savedPrompts.map((item) => (
              <option key={item.name}>{item.name}</option>
            ))}
          </select>
        </label>
      )}
      {gen.savedPrompts.length > 0 ? (
        <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => set({ savedPrompts: gen.savedPrompts.filter((item) => item.name !== gen.promptName) })}>
          Delete saved prompt
        </button>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <Num label="Steps" value={gen.steps} onChange={(steps) => set({ steps })} />
        <Num label="CFG" value={gen.cfg} onChange={(cfg) => set({ cfg })} />
        <Num label="Batch count" value={gen.batch} onChange={(batch) => set({ batch })} />
        <Num label="Width" value={gen.width} onChange={(width) => set({ width })} />
        <Num label="Height" value={gen.height} onChange={(height) => set({ height })} />
        <label className="field">
          Seed, blank is random
          <input value={gen.seed} onChange={(event) => set({ seed: event.target.value })} />
        </label>
      </div>
      <label className="field">
        Model
        <input value={gen.model} onChange={(event) => set({ model: event.target.value })} placeholder="checkpoint path or name" />
      </label>
      <label className="field">
        Extra models, one per line
        <textarea value={gen.models} onChange={(event) => set({ models: event.target.value })} />
      </label>
      <label className="field">
        CLIP
        <input value={gen.clip} onChange={(event) => set({ clip: event.target.value })} />
      </label>
      <label className="field">
        CLIP-G, SDXL only
        <input value={gen.clipG} onChange={(event) => set({ clipG: event.target.value })} />
      </label>
      <label className="field">
        VAE
        <input value={gen.vae} onChange={(event) => set({ vae: event.target.value })} />
      </label>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={gen.tile} onChange={(event) => set({ tile: event.target.checked })} />
        Tile the VAE
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <Num label="Tile" value={gen.tileSize} onChange={(tileSize) => set({ tileSize })} />
        <Num label="Overlap" value={gen.tileOverlap} onChange={(tileOverlap) => set({ tileOverlap })} />
      </div>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={gen.eyes} onChange={(event) => set({ eyes: event.target.checked })} />
        Redraw eyes
      </label>
      <label className="field">
        Eye detector file
        <input value={gen.eyeFile} onChange={(event) => set({ eyeFile: event.target.value })} />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <Num label="Denoise" value={gen.eyeDenoise} onChange={(eyeDenoise) => set({ eyeDenoise })} />
        <Num label="Confidence" value={gen.eyeConfidence} onChange={(eyeConfidence) => set({ eyeConfidence })} />
      </div>
      <label className="field">
        Eye prompt
        <input value={gen.eyePrompt} onChange={(event) => set({ eyePrompt: event.target.value })} />
      </label>
      <p className="mt-4 text-sm">LoRAs</p>
      {gen.loras.map((lora, index) => (
        <div key={index} className="mt-2 grid gap-2 sm:grid-cols-[1fr_6rem]">
          <input className="box" value={lora.path} placeholder="LoRA file" onChange={(event) => set({ loras: gen.loras.map((item, i) => (i === index ? { ...item, path: event.target.value } : item)) })} />
          <input className="box" type="number" value={lora.weight} onChange={(event) => set({ loras: gen.loras.map((item, i) => (i === index ? { ...item, weight: Number(event.target.value) } : item)) })} />
        </div>
      ))}
      <button type="button" className="mt-2 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => set({ loras: [...gen.loras, { path: "", weight: 1 }] })}>
        Add LoRA
      </button>
      <label className="field">
        Image save location
        <input value={gen.output} onChange={(event) => set({ output: event.target.value })} />
      </label>
    </div>
  );
}

function Captions({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  const cap = desk.captions;
  function set(partial: Partial<Desk["captions"]>) {
    patch({ captions: { ...cap, ...partial } });
  }
  return (
    <div>
      <h2 className="display text-2xl">Captions</h2>
      <label className="field">
        Caption with
        <select className="box" value={cap.engine} onChange={(event) => set({ engine: event.target.value as Desk["captions"]["engine"] })}>
          <option value="kobold">KoboldAI</option>
          <option value="clip">CLIP Vision</option>
          <option value="joy">JoyCaption Beta One</option>
        </select>
      </label>
      <label className="field">
        What the pictures are
        <select className="box" value={cap.kind} onChange={(event) => set({ kind: event.target.value as Desk["captions"]["kind"] })}>
          <option value="character">Character</option>
          <option value="style">Style</option>
          <option value="concept">Concept</option>
        </select>
      </label>
      {cap.engine === "kobold" && <p className="mt-2 text-sm text-[var(--muted)]">Uses the Kobold address on the Card tab.</p>}
      {cap.engine === "clip" && (
        <>
          <label className="field">
            CLIP Vision file
            <input value={cap.vision} onChange={(event) => set({ vision: event.target.value })} />
          </label>
          <label className="field">
            Matching CLIP text file
            <input value={cap.visionText} onChange={(event) => set({ visionText: event.target.value })} />
          </label>
        </>
      )}
      {cap.engine === "joy" && (
        <>
          <label className="field">
            JoyCaption GGUF
            <input value={cap.joy} onChange={(event) => set({ joy: event.target.value })} />
          </label>
          <label className="field">
            mmproj
            <input value={cap.mmproj} onChange={(event) => set({ mmproj: event.target.value })} />
          </label>
        </>
      )}
      <label className="field">
        What to ask
        <textarea value={cap.ask} onChange={(event) => set({ ask: event.target.value })} />
      </label>
      <label className="field">
        Trigger word
        <input value={cap.trigger} onChange={(event) => set({ trigger: event.target.value })} />
      </label>
      <label className="field">
        Pictures, one path per line
        <textarea value={cap.files} onChange={(event) => set({ files: event.target.value })} />
      </label>
      <label className="field">
        Training folder
        <input value={cap.folder} onChange={(event) => set({ folder: event.target.value })} />
      </label>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={cap.copyPictures} onChange={(event) => set({ copyPictures: event.target.checked })} />
        Copy pictures into the folder
      </label>
      <label className="flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={cap.skipExisting} onChange={(event) => set({ skipExisting: event.target.checked })} />
        Skip pictures that already have a caption
      </label>
    </div>
  );
}

function Train({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  const train = desk.train;
  const hints = {
    character: "A person. The trigger word is their name. Rank 32, alpha 16.",
    style: "A look. The trigger word is the style name. Rank 16, alpha 16.",
    concept: "An object or idea. The trigger word is the concept. Rank 16, alpha 8.",
  };
  function set(partial: Partial<Desk["train"]>) {
    patch({ train: { ...train, ...partial } });
  }
  return (
    <div>
      <h2 className="display text-2xl">Train a LoRA</h2>
      <p className="text-sm text-[var(--muted)]">Uses the model selected on Generate. A matching .txt file captions each picture.</p>
      <label className="field">
        What you are training
        <select
          className="box"
          value={train.subject}
          onChange={(event) => {
            const subject = event.target.value as Desk["train"]["subject"];
            const preset = subject === "character" ? { rank: 32, alpha: 16 } : subject === "style" ? { rank: 16, alpha: 16 } : { rank: 16, alpha: 8 };
            set({ subject, ...preset });
          }}
        >
          <option value="character">Character / likeness</option>
          <option value="style">A specific style</option>
          <option value="concept">A concept</option>
        </select>
      </label>
      <p className="mt-2 text-sm text-[var(--muted)]">{hints[train.subject]}</p>
      <label className="field">
        Image folder
        <input value={train.folder} onChange={(event) => set({ folder: event.target.value })} />
      </label>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="field">
          Trigger word
          <input value={train.trigger} onChange={(event) => set({ trigger: event.target.value })} />
        </label>
        <label className="field">
          LoRA name
          <input value={train.name} onChange={(event) => set({ name: event.target.value })} />
        </label>
        <Num label="Network rank" value={train.rank} onChange={(rank) => set({ rank })} />
        <Num label="Network alpha" value={train.alpha} onChange={(alpha) => set({ alpha })} />
        <label className="field">
          Learning rate
          <input value={train.lr} onChange={(event) => set({ lr: event.target.value })} />
        </label>
        <Num label="Steps" value={train.steps} onChange={(steps) => set({ steps })} />
        <Num label="Resolution" value={train.resolution} onChange={(resolution) => set({ resolution })} />
      </div>
      {(
        [
          ["buckets", "Aspect-ratio buckets"],
          ["checkpoint", "Gradient checkpointing"],
          ["cache", "Cache latents"],
          ["noHalf", "No half VAE"],
        ] as const
      ).map(([key, label]) => (
        <label key={key} className="mt-2 flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={train[key]} onChange={(event) => set({ [key]: event.target.checked })} />
          {label}
        </label>
      ))}
    </div>
  );
}

function Library({ desk, patch }: { desk: Desk; patch: (p: Partial<Desk>) => void }) {
  const [query, setQuery] = useState("");
  const cards = desk.library.filter((row) => `${row.card.name} ${row.title} ${row.card.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase()));
  return (
    <section className="pane">
      <h2 className="display text-2xl">Library</h2>
      <input className="box mt-3 max-w-md" value={query} placeholder="Search characters/tags" onChange={(event) => setQuery(event.target.value)} />
      <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((row) => (
          <li key={row.id} className="rounded-md border border-[var(--line)] bg-[var(--surface)] p-3">
            <button
              type="button"
              className="w-full text-left"
              onClick={() => patch({ card: row.card, title: row.title, favorite: row.favorite, portrait: row.portrait, concept: row.concept ?? "", openCardId: row.id, greetings: row.card.alternate_greetings.join("\n---\n"), mode: "characters", editorTab: "card" })}
            >
              <strong>{row.card.name || "Unnamed"}</strong>
              {row.favorite ? <span className="ml-2 text-[var(--red)]">★</span> : null}
              <p className="text-xs text-[var(--muted)]">{row.title || row.card.creator}</p>
              <p className="mt-1 line-clamp-2 text-sm">{row.card.summary || row.card.description}</p>
            </button>
          </li>
        ))}
      </ul>
      {cards.length === 0 ? <p className="mt-4 text-sm text-[var(--muted)]">Keep a card from the editor and it shows up here.</p> : null}
      <h3 className="display mt-8 text-xl">Personas</h3>
      <ul className="mt-2 space-y-2">
        {desk.personas.map((row) => (
          <li key={row.id}>
            <button type="button" className="min-h-11 text-sm" onClick={() => patch({ card: row.card, title: row.title, concept: row.concept ?? "", openCardId: row.id, greetings: row.card.alternate_greetings.join("\n---\n"), mode: "personas", personaMode: true, editorTab: "card" })}>
              {row.card.name || "Unnamed persona"}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Num({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="field">
      {label}
      <input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}
