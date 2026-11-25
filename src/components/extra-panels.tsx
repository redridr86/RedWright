import type { Desk, LoreEntry, Sampler } from "@/lib/desk";
import { novelDefaults } from "@/lib/desk";

type Patch = (partial: Partial<Desk>) => void;

export function Onboarding({ desk, patch }: { desk: Desk; patch: Patch }) {
  return (
    <div>
      <p className="text-sm text-[var(--muted)]">Questions asked the first time someone opens a chat with this card. They are not sent on later turns.</p>
      {desk.onboarding.map((step) => (
        <div key={step.id} className="mt-3 rounded-md border border-[var(--line)] p-3">
          <label className="field">
            Step title
            <input
              value={step.title}
              onChange={(event) =>
                patch({ onboarding: desk.onboarding.map((item) => (item.id === step.id ? { ...item, title: event.target.value } : item)) })
              }
            />
          </label>
          <label className="field">
            What to ask
            <textarea
              value={step.prompt}
              onChange={(event) =>
                patch({ onboarding: desk.onboarding.map((item) => (item.id === step.id ? { ...item, prompt: event.target.value } : item)) })
              }
            />
          </label>
          <label className="mt-2 flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={step.enabled}
              onChange={(event) =>
                patch({ onboarding: desk.onboarding.map((item) => (item.id === step.id ? { ...item, enabled: event.target.checked } : item)) })
              }
            />
            Ask this step
          </label>
        </div>
      ))}
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() => patch({ onboarding: [...desk.onboarding, { id: crypto.randomUUID(), title: "New step", prompt: "", enabled: true }] })}
      >
        Add step
      </button>
    </div>
  );
}

export function Convo({ desk, patch }: { desk: Desk; patch: Patch }) {
  const convo = desk.convo;
  return (
    <div>
      <p className="text-sm text-[var(--muted)]">The conversation profile used when Chat sends a turn to KoboldCPP.</p>
      <label className="field">
        Profile name
        <input value={convo.name} onChange={(event) => patch({ convo: { ...convo, name: event.target.value } })} />
      </label>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="field">
          Temperature
          <input type="number" step="0.05" value={convo.temperature} onChange={(event) => patch({ convo: { ...convo, temperature: Number(event.target.value) } })} />
        </label>
        <label className="field">
          Max tokens
          <input type="number" value={convo.maxTokens} onChange={(event) => patch({ convo: { ...convo, maxTokens: Number(event.target.value) } })} />
        </label>
        <label className="field">
          Top P
          <input type="number" step="0.01" value={convo.topP} onChange={(event) => patch({ convo: { ...convo, topP: Number(event.target.value) } })} />
        </label>
      </div>
      <label className="field">
        Instruct
        <textarea value={convo.instruct} onChange={(event) => patch({ convo: { ...convo, instruct: event.target.value } })} />
      </label>
      <label className="field">
        Stop sequences, one per line
        <textarea value={convo.stops} onChange={(event) => patch({ convo: { ...convo, stops: event.target.value } })} />
      </label>
    </div>
  );
}

export function Sprites({ desk, patch }: { desk: Desk; patch: Patch }) {
  const kinds = [
    ["face", "Facial expressions"],
    ["body", "Full-body"],
    ["clip", "Clips"],
  ] as const;
  const layout = desk.spriteLayout;
  const visible = desk.sprites.filter((sprite) => sprite.kind === desk.spriteKind);
  return (
    <div>
      <div className="mt-3 flex flex-wrap gap-2">
        {kinds.map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => patch({ spriteKind: id })}
            className={`min-h-11 rounded-md px-3 text-sm ${desk.spriteKind === id ? "bg-[var(--red)] font-semibold text-white" : "border border-[var(--line)]"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-[var(--muted)]">
        Names the pose or mood. The Windows app and NovelAI can paint the file later. Transparent PNG works best for full-body.
      </p>
      {visible.map((sprite) => (
        <div key={sprite.id} className="mt-3 grid gap-2 rounded-md border border-[var(--line)] p-3 sm:grid-cols-[1fr_1fr_auto]">
          <label className="field mt-0">
            Label
            <input
              value={sprite.label}
              onChange={(event) =>
                patch({ sprites: desk.sprites.map((item) => (item.id === sprite.id ? { ...item, label: event.target.value } : item)) })
              }
            />
          </label>
          <label className="field mt-0">
            File or note
            <input
              value={sprite.note}
              onChange={(event) =>
                patch({ sprites: desk.sprites.map((item) => (item.id === sprite.id ? { ...item, note: event.target.value } : item)) })
              }
            />
          </label>
          <button
            type="button"
            className="min-h-11 self-end rounded-md border border-[var(--line)] px-3 text-sm"
            onClick={() => patch({ sprites: desk.sprites.filter((item) => item.id !== sprite.id) })}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() =>
          patch({
            sprites: [
              ...desk.sprites,
              { id: crypto.randomUUID(), kind: desk.spriteKind, label: desk.spriteKind === "face" ? "neutral" : "idle", note: "" },
            ],
          })
        }
      >
        Add sprite
      </button>
      <h3 className="display mt-6 text-xl">Layout</h3>
      <label className="field">
        Default side
        <select className="box" value={layout.side} onChange={(event) => patch({ spriteLayout: { ...layout, side: event.target.value as "left" | "right" } })}>
          <option value="left">Left</option>
          <option value="right">Right</option>
        </select>
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        {(
          [
            ["expressionSize", "Expression size"],
            ["bodySize", "Full-body size"],
            ["expressionOpacity", "Expression opacity"],
            ["bodyOpacity", "Full-body opacity"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="field">
            {label} {layout[key]}%
            <input
              type="range"
              min={key.endsWith("Size") ? 5 : 0}
              max={key.endsWith("Size") ? 200 : 100}
              value={layout[key]}
              onChange={(event) => patch({ spriteLayout: { ...layout, [key]: Number(event.target.value) } })}
            />
          </label>
        ))}
      </div>
    </div>
  );
}

export function Lorebooks({ desk, patch }: { desk: Desk; patch: Patch }) {
  return (
    <section className="pane">
      <h2 className="display text-2xl">Lorebooks</h2>
      <p className="text-sm text-[var(--muted)]">Link a book to the open card, or mark it global so every chat can scan it.</p>
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md bg-[var(--red)] px-3 text-sm font-semibold text-white"
        onClick={() =>
          patch({
            lorebooks: [
              { id: crypto.randomUUID(), name: "New lorebook", category: "Character", description: "", global: false, embedded: false, entries: [] },
              ...desk.lorebooks,
            ],
          })
        }
      >
        New lorebook
      </button>
      {desk.lorebooks.map((book) => (
        <article key={book.id} className="mt-4 rounded-md border border-[var(--line)] p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="field mt-0">
              Name
              <input value={book.name} onChange={(event) => updateBook(desk, patch, book.id, { name: event.target.value })} />
            </label>
            <label className="field mt-0">
              Category
              <select
                className="box"
                value={book.category}
                onChange={(event) => updateBook(desk, patch, book.id, { category: event.target.value as Desk["lorebooks"][number]["category"] })}
              >
                {["World", "Character", "NPC", "Spellbook", "Other"].map((category) => (
                  <option key={category}>{category}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="field">
            Description
            <textarea value={book.description} onChange={(event) => updateBook(desk, patch, book.id, { description: event.target.value })} />
          </label>
          <div className="mt-2 flex flex-wrap gap-3 text-sm">
            <label className="flex min-h-11 items-center gap-2">
              <input type="checkbox" checked={book.global} onChange={(event) => updateBook(desk, patch, book.id, { global: event.target.checked })} />
              Global
            </label>
            <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3" onClick={() => addEntry(desk, patch, book.id)}>
              Add entry
            </button>
            <button
              type="button"
              className="min-h-11 rounded-md border border-[var(--line)] px-3"
              onClick={() =>
                patch({
                  lore: [...desk.lore, ...book.entries.map((entry) => ({ ...entry, id: crypto.randomUUID() }))],
                  lorebooks: desk.lorebooks.map((item) => (item.id === book.id ? { ...item, embedded: true } : item)),
                  status: "Embedded into the open card.",
                })
              }
            >
              {book.embedded ? "Embedded" : "Embed into card"}
            </button>
            <button type="button" className="min-h-11 px-3 text-[var(--muted)]" onClick={() => patch({ lorebooks: desk.lorebooks.filter((item) => item.id !== book.id) })}>
              Delete
            </button>
          </div>
          {book.entries.map((entry) => (
            <EntryRow key={entry.id} entry={entry} onChange={(next) => updateEntry(desk, patch, book.id, next)} />
          ))}
        </article>
      ))}
      {desk.lorebooks.length === 0 ? <p className="mt-4 text-sm text-[var(--muted)]">No lorebooks yet.</p> : null}
    </section>
  );
}

function updateBook(desk: Desk, patch: Patch, id: string, partial: Partial<Desk["lorebooks"][number]>) {
  patch({ lorebooks: desk.lorebooks.map((book) => (book.id === id ? { ...book, ...partial } : book)) });
}

function addEntry(desk: Desk, patch: Patch, id: string) {
  patch({
    lorebooks: desk.lorebooks.map((book) =>
      book.id === id ? { ...book, entries: [...book.entries, { id: crypto.randomUUID(), keys: "", content: "", enabled: true }] } : book,
    ),
  });
}

function updateEntry(desk: Desk, patch: Patch, bookId: string, entry: LoreEntry) {
  patch({
    lorebooks: desk.lorebooks.map((book) =>
      book.id === bookId ? { ...book, entries: book.entries.map((item) => (item.id === entry.id ? entry : item)) } : book,
    ),
  });
}

function EntryRow({ entry, onChange }: { entry: LoreEntry; onChange: (entry: LoreEntry) => void }) {
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      <label className="field mt-0">
        Keys
        <input value={entry.keys} onChange={(event) => onChange({ ...entry, keys: event.target.value })} />
      </label>
      <label className="field mt-0">
        Content
        <textarea value={entry.content} onChange={(event) => onChange({ ...entry, content: event.target.value })} />
      </label>
    </div>
  );
}

export function Life({ desk, patch }: { desk: Desk; patch: Patch }) {
  return (
    <section className="pane">
      <h2 className="display text-2xl">Life</h2>
      <p className="text-sm text-[var(--muted)]">A timeline that travels with the card. Pinned beats are copied into long memory when you export.</p>
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() => patch({ life: [{ id: crypto.randomUUID(), when: "", title: "", body: "" }, ...desk.life] })}
      >
        Add beat
      </button>
      {desk.life.map((beat) => (
        <div key={beat.id} className="mt-3 rounded-md border border-[var(--line)] p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="field mt-0">
              When
              <input value={beat.when} onChange={(event) => patch({ life: desk.life.map((item) => (item.id === beat.id ? { ...item, when: event.target.value } : item)) })} />
            </label>
            <label className="field mt-0">
              Title
              <input value={beat.title} onChange={(event) => patch({ life: desk.life.map((item) => (item.id === beat.id ? { ...item, title: event.target.value } : item)) })} />
            </label>
          </div>
          <label className="field">
            What happened
            <textarea value={beat.body} onChange={(event) => patch({ life: desk.life.map((item) => (item.id === beat.id ? { ...item, body: event.target.value } : item)) })} />
          </label>
          <button type="button" className="mt-2 min-h-11 text-sm text-[var(--muted)]" onClick={() => patch({ life: desk.life.filter((item) => item.id !== beat.id) })}>
            Remove
          </button>
        </div>
      ))}
    </section>
  );
}

export function Presets({ desk, patch }: { desk: Desk; patch: Patch }) {
  return (
    <section className="pane">
      <h2 className="display text-2xl">Presets</h2>
      <p className="text-sm text-[var(--muted)]">Sampler presets for KoboldCPP writing and chat. The active one is what Write card and Chat use.</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="field mt-0">
          Kobold address
          <input value={desk.kobold} onChange={(event) => patch({ kobold: event.target.value })} />
        </label>
        <label className="field mt-0">
          API key
          <input type="password" value={desk.koboldKey} onChange={(event) => patch({ koboldKey: event.target.value })} />
        </label>
        <label className="field">
          NovelAI token
          <input type="password" value={desk.novelToken} onChange={(event) => patch({ novelToken: event.target.value })} />
        </label>
        <label className="field">
          NovelAI model
          <input value={desk.novelModel} onChange={(event) => patch({ novelModel: event.target.value })} />
        </label>
      </div>
      {desk.presets.map((preset) => (
        <article key={preset.id} className={`mt-4 rounded-md border p-3 ${desk.activePreset === preset.id ? "border-[var(--red)]" : "border-[var(--line)]"}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="field mt-0 min-w-40 flex-1">
              Name
              <input value={preset.name} onChange={(event) => updatePreset(desk, patch, preset.id, { name: event.target.value })} />
            </label>
            <button type="button" className="min-h-11 rounded-md bg-[var(--red)] px-3 text-sm font-semibold text-white" onClick={() => patch({ activePreset: preset.id })}>
              {desk.activePreset === preset.id ? "Active" : "Use"}
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Num label="Temperature" value={preset.temperature} step="0.05" onChange={(temperature) => updatePreset(desk, patch, preset.id, { temperature })} />
            <Num label="Top P" value={preset.topP} step="0.01" onChange={(topP) => updatePreset(desk, patch, preset.id, { topP })} />
            <Num label="Top K" value={preset.topK} onChange={(topK) => updatePreset(desk, patch, preset.id, { topK })} />
            <Num label="Min P" value={preset.minP} step="0.01" onChange={(minP) => updatePreset(desk, patch, preset.id, { minP })} />
            <Num label="Repetition penalty" value={preset.repPen} step="0.01" onChange={(repPen) => updatePreset(desk, patch, preset.id, { repPen })} />
            <Num label="Max tokens" value={preset.maxTokens} onChange={(maxTokens) => updatePreset(desk, patch, preset.id, { maxTokens })} />
          </div>
        </article>
      ))}
      <button
        type="button"
        className="mt-3 min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
        onClick={() =>
          patch({
            presets: [...desk.presets, { id: crypto.randomUUID(), name: "Custom", temperature: 0.8, topP: 0.95, topK: 0, minP: 0.05, repPen: 1.1, maxTokens: 800 }],
          })
        }
      >
        New preset
      </button>
    </section>
  );
}

function updatePreset(desk: Desk, patch: Patch, id: string, partial: Partial<Sampler>) {
  patch({ presets: desk.presets.map((preset) => (preset.id === id ? { ...preset, ...partial } : preset)) });
}

function Num({ label, value, onChange, step }: { label: string; value: number; onChange: (value: number) => void; step?: string }) {
  return (
    <label className="field">
      {label}
      <input type="number" step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

export function PictureLibrary({ desk, patch }: { desk: Desk; patch: Patch }) {
  const names = desk.picList.split("\n").map((line) => line.trim()).filter(Boolean);
  return (
    <div>
      <h2 className="display text-2xl">Picture library</h2>
      <p className="text-sm text-[var(--muted)]">The folder RedGen scans on your PC. Subfolders stay optional, same as the desktop library tab.</p>
      <label className="field">
        Folder
        <input value={desk.picFolder} onChange={(event) => patch({ picFolder: event.target.value })} placeholder="C:\\Pictures\\RedWright" />
      </label>
      <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input type="checkbox" checked={desk.picSubs} onChange={(event) => patch({ picSubs: event.target.checked })} />
        Include subfolders
      </label>
      <label className="field">
        Picture names, one per line
        <textarea value={desk.picList} onChange={(event) => patch({ picList: event.target.value })} placeholder="seed-12.png" />
      </label>
      <p className="mt-2 text-sm text-[var(--muted)]">{names.length ? `${names.length} pictures listed.` : "No pictures listed yet."}</p>
      <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {names.slice(0, 24).map((name) => (
          <li key={name} className="truncate rounded-md border border-[var(--line)] bg-[var(--surface)] px-2 py-3 text-xs text-[var(--muted)]">
            {name}
          </li>
        ))}
      </ul>
    </div>
  );
}

const NOVEL_MODELS = [
  ["V5 Full", "nai-diffusion-5-full"],
  ["V5 Curated", "nai-diffusion-5-curated"],
  ["V4.5 Full", "nai-diffusion-4-5-full"],
  ["V4.5 Curated", "nai-diffusion-4-5-curated"],
] as const;

const NOVEL_SAMPLERS = ["k_euler_ancestral", "k_euler", "k_dpmpp_2s_ancestral", "k_dpmpp_2m", "k_dpmpp_sde", "k_dpmpp_2m_sde"];
const NOVEL_SCHEDULES = ["karras", "exponential", "polyexponential"];

export function Novel({ desk, patch }: { desk: Desk; patch: Patch }) {
  const setup = desk.novelSetup;
  function set(partial: Partial<Desk["novelSetup"]>) {
    patch({ novelSetup: { ...setup, ...partial } });
  }
  const v5 = desk.novelModel.includes("diffusion-5");
  const width = setup.autoSize ? "from character count" : `${setup.width}×${setup.height}`;
  function useAppearance() {
    const text = [desk.card.appearance, desk.card.name, desk.card.scenario].map((part) => part.trim()).filter(Boolean).join(", ");
    patch({
      generate: { ...desk.generate, prompt: text },
      status: text ? "Appearance is the NovelAI prompt. Draw on the Windows app sends it." : "Write an appearance on the card first.",
    });
  }
  return (
    <section className="pane">
      <h2 className="display text-2xl">NovelAI</h2>
      <p className="text-sm text-[var(--muted)]">Same page as the Windows NovelAI tab. Draw and Test run there, with this token and these settings. V5 does not use the AMD GPU.</p>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-[var(--line)] p-3">
          <h3 className="display text-xl">Prompt</h3>
          <textarea
            className="box mt-2 min-h-40 w-full"
            value={desk.generate.prompt}
            onChange={(event) => patch({ generate: { ...desk.generate, prompt: event.target.value } })}
            placeholder="Age, species, body description, or Danbooru tags"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={useAppearance}>
              Use appearance
            </button>
            <button
              type="button"
              className="min-h-11 rounded-md bg-[var(--red)] px-4 text-sm text-white"
              onClick={() => patch({ status: "Draw runs on the Windows app. Open NovelAI there and press Draw. This page keeps the token and the setup." })}
            >
              Draw
            </button>
            <button
              type="button"
              className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm"
              onClick={() => patch({ status: "Test NovelAI runs on the Windows app. It checks the persistent token and does not spend Anlas." })}
            >
              Test NovelAI
            </button>
          </div>
          <p className="mt-2 text-xs text-[var(--muted)]">Requested size is {width} unless character count changes it. A draw sends Anlas.</p>
          <div className="mt-3 flex min-h-64 items-center justify-center rounded-md border border-[var(--line)] bg-[var(--bg)] px-4 text-center text-sm text-[var(--muted)]">
            The picture lands on the Windows NovelAI tab. Save it there, or use it on the card.
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="min-h-11 flex-1 rounded-md bg-[var(--red)] px-3 text-sm text-white" onClick={() => patch({ status: "Save the picture from the Windows NovelAI tab." })}>
              Save
            </button>
            <button type="button" className="min-h-11 flex-1 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => patch({ status: "Use on card is on the Windows NovelAI tab, after a picture is drawn." })}>
              Use on card
            </button>
          </div>
          {desk.status ? <p className="mt-2 text-sm text-[var(--muted)]">{desk.status}</p> : null}
        </div>
        <div className="grid content-start gap-3">
          <div className="rounded-md border border-[var(--line)] p-3">
            <h3 className="display text-xl">Account</h3>
            <label className="field">
              Persistent token
              <input type="password" value={desk.novelToken} onChange={(event) => patch({ novelToken: event.target.value })} />
            </label>
            <p className="mt-1 text-xs text-[var(--muted)]">The pst- token stays on this computer and is sent only to NovelAI.</p>
            <label className="field">
              Model
              <select className="box" value={desk.novelModel} onChange={(event) => patch({ novelModel: event.target.value })}>
                {NOVEL_MODELS.map(([label, id]) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="rounded-md border border-[var(--line)] p-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="display text-xl">NovelAI generation setup</h3>
              <button type="button" className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm" onClick={() => set(novelDefaults)}>
                Reset
              </button>
            </div>
            <p className="text-xs text-[var(--muted)]">Prompt prefixes, sampler, scheduler, steps, guidance, seed, and resolution.</p>
            <p className="mt-1 text-xs text-[var(--muted)]">Seed -1 keeps generation random. Any non-negative seed is reused exactly.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="field">
                Seed
                <input value={setup.seed} onChange={(event) => set({ seed: event.target.value })} />
              </label>
              <div>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-sm text-[var(--muted)]">Style profile</span>
                  <button type="button" className="min-h-11 rounded-full border border-[var(--line)] px-3 text-xs" onClick={() => set({ style: "Anime" })}>
                    Use Danbooru / Illustrious
                  </button>
                </div>
                <select className="box mt-1 w-full" value={setup.style} onChange={(event) => set({ style: event.target.value })}>
                  <option>Anime</option>
                  <option>Semi-realistic</option>
                  <option>Furry</option>
                </select>
                <p className="mt-1 text-xs text-[var(--muted)]">Suggested from model/source: Danbooru / Illustrious</p>
              </div>
              <Num label="Steps" value={setup.steps} onChange={(steps) => set({ steps })} />
              <Num label="Prompt guidance" value={setup.guidance} step="0.1" onChange={(guidance) => set({ guidance })} />
              <Num label="Guidance rescale" value={setup.rescale} step="0.01" onChange={(rescale) => set({ rescale })} />
              <Num label="UC preset" value={setup.uc} onChange={(uc) => set({ uc })} />
            </div>
            <p className="mt-1 text-xs text-[var(--muted)]">UC preset: 0 heavy, 1 light, 2 human focus, 3 none, 4 as in your setup.</p>
            <label className="field">
              Prompt prefix
              <textarea value={setup.prefix} onChange={(event) => set({ prefix: event.target.value })} />
            </label>
            <label className="field">
              Negative prefix
              <textarea value={setup.negative} onChange={(event) => set({ negative: event.target.value })} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="field">
                Sampler
                <select className="box" value={setup.sampler} onChange={(event) => set({ sampler: event.target.value })}>
                  {NOVEL_SAMPLERS.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Noise schedule
                <select className="box" value={setup.schedule} onChange={(event) => set({ schedule: event.target.value })}>
                  {NOVEL_SCHEDULES.map((name) => (
                    <option key={name}>{name}</option>
                  ))}
                </select>
              </label>
            </div>
            <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" checked={setup.autoSize} onChange={(event) => set({ autoSize: event.target.checked })} />
              Choose resolution from character count
            </label>
            <p className="text-xs text-[var(--muted)]">Uses portrait for one subject, square for two, and landscape for three or more. Free-form prompts without a detectable count keep the requested size.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Num label="Width" value={setup.width} onChange={(width) => set({ width })} />
              <Num label="Height" value={setup.height} onChange={(height) => set({ height })} />
            </div>
            <div className="mt-4 flex items-start justify-between gap-2">
              <div>
                <h3 className="display text-xl">NovelAI V4.5 style plate</h3>
                <p className="text-xs text-[var(--muted)]">
                  {v5
                    ? "V5 does not take a style plate. Switch to V4.5 to use it."
                    : "A persistent style-only reference applied first to every V4.5 generation, including scenes without characters."}
                </p>
              </div>
            </div>
            <label className="field">
              Style plate file
              <input value={setup.plate} onChange={(event) => set({ plate: event.target.value })} placeholder="Choose image on the Windows tab" />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <Num label="Style strength" value={setup.strength} step="0.05" onChange={(strength) => set({ strength })} />
              <Num label="Style fidelity" value={setup.fidelity} step="0.05" onChange={(fidelity) => set({ fidelity })} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
