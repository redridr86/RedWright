import { useMemo, useState, type ReactNode } from "react";
import { Copy, Download, ImagePlus, Plus, RefreshCw, Shuffle, Star, Trash2, Upload } from "lucide-react";
import { koboldRoot, type Card } from "@/lib/cards";
import type { Desk, RefPic } from "@/lib/desk";

const STARTERS: [string, string][] = [
  ["Night librarian", "A night librarian who shelves books that only exist between midnight and dawn, and already knows the reader's name."],
  ["Orbital welder", "An orbital welder who patches the station hull on twelve-hour shifts and talks to the dark like it might answer."],
  ["Last dragon", "The last dragon in a drowned valley, keeping a human village because the old bargain still stands."],
  ["Dock rigger", "A dock rigger who can tell a ship's cargo by the way it sits in the water, and who does not ask questions."],
  ["Flood courier", "A flood courier who carries letters across a city that is slowly going under, and never opens them."],
  ["Quiet archivist", "A quiet archivist of other people's secrets, paid to remember what the city would rather lose."],
  ["Train cook", "A train cook on a line that no longer appears on maps, feeding whoever is still riding."],
  ["Lighthouse keeper", "A lighthouse keeper on a coast where the light is for something that is not ships."],
  ["Map mender", "A map mender who stitches streets back onto paper after the city rearranges itself overnight."],
  ["Garden locksmith", "A garden locksmith who makes keys for gates that only open for one person, once."],
];

const FIELDS: { key: keyof Card; label: string; hint: string; rows: number }[] = [
  { key: "description", label: "Description", hint: "Identity and role. Marinara sends this every turn.", rows: 6 },
  { key: "personality", label: "Personality", hint: "Speech, temperament, and habits. Specific beats a pile of adjectives.", rows: 5 },
  { key: "backstory", label: "Backstory", hint: "Marinara extension. Origin, relationships, facts that stay true.", rows: 5 },
  { key: "appearance", label: "Appearance", hint: "Marinara extension. Face, build, clothes, and visual detail.", rows: 5 },
  { key: "scenario", label: "Scenario", hint: "The situation a new chat starts in.", rows: 4 },
  { key: "first_mes", label: "First message", hint: "The opening. Actions in asterisks.", rows: 5 },
  { key: "mes_example", label: "Examples", hint: "Separate exchanges with <START>. Teaches the voice.", rows: 5 },
  { key: "creator_notes", label: "Creator notes", hint: "For people reading the card. Not sent to the model.", rows: 3 },
  { key: "system_prompt", label: "System prompt", hint: "Optional. Leave blank to keep Marinara's own instructions.", rows: 4 },
  { key: "post_history_instructions", label: "After history", hint: "Optional instructions placed after the chat log.", rows: 4 },
];

function words(text: string) {
  const count = text.trim() ? text.trim().split(/\s+/).length : 0;
  return `${count} word${count === 1 ? "" : "s"}`;
}

function bump(version: string) {
  const match = version.match(/^(\d+)\.(\d+)/);
  if (!match) return "1.1";
  return `${match[1]}.${Number(match[2]) + 1}`;
}

export { bump };

export function CardDesk({
  desk,
  patch,
  patchCard,
  busy,
  extras,
  onWrite,
  onRewrite,
  onOpen,
  onRemove,
  onKeep,
  onNew,
  onJson,
  onPng,
  onCopy,
  onImport,
}: {
  desk: Desk;
  patch: (partial: Partial<Desk>) => void;
  patchCard: (partial: Partial<Card>) => void;
  busy: boolean;
  extras: ReactNode;
  onWrite: () => void;
  onRewrite: (field: keyof Card, label: string) => void;
  onOpen: (row: Desk["library"][number]) => void;
  onRemove: (id: string) => void;
  onKeep: () => void;
  onNew: () => void;
  onJson: () => void;
  onPng: () => void;
  onCopy: () => void;
  onImport: (file: File | undefined) => void;
}) {
  const [order, setOrder] = useState(STARTERS);
  const rows = desk.mode === "personas" || desk.personaMode ? desk.personas.map((row) => ({ ...row, favorite: false, portrait: "" })) : desk.library;
  const personaId = desk.activePersona;
  const sheetName = desk.card.name.trim() || "Unnamed";
  const nameColor = desk.look.nameColor || "var(--accent)";
  const dialogue = desk.look.dialogue || "var(--ink)";
  const box = desk.look.messageBox || "var(--paper)";
  const book = useMemo(() => desk.lorebooks.find((item) => item.id === desk.linkedBook), [desk.lorebooks, desk.linkedBook]);

  function addFiles(list: FileList | File[] | null) {
    const files = Array.from(list ?? []).filter((file) => file.type.startsWith("image/"));
    if (!files.length) return;
    Promise.all(
      files.map(
        (file) =>
          new Promise<RefPic>((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve({ id: crypto.randomUUID(), name: file.name, url: String(reader.result || "") });
            reader.readAsDataURL(file);
          }),
      ),
    ).then((pics) => {
      const first = pics[0];
      patch({
        references: [...desk.references, ...pics],
        starredRef: desk.starredRef || first.id,
        portrait: desk.portrait || first.url,
        status: "Reference added. The starred picture is the portrait.",
      });
    });
  }

  function star(pic: RefPic) {
    patch({ starredRef: pic.id, portrait: pic.url, status: "That picture is the portrait." });
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

  return (
    <div className="desk-columns">
      <div className="desk-col">
        <section className="slab">
          <h2>Concept</h2>
          <textarea
            value={desk.concept}
            placeholder="Who are they, where are they, and what should a chat feel like?"
            onChange={(event) => patch({ concept: event.target.value })}
          />
          <button type="button" className="btn-accent" style={{ marginTop: "0.8rem" }} disabled={busy} onClick={onWrite}>
            <RefreshCw size={16} /> Write the card
          </button>
          <label className="check">
            <input type="checkbox" checked={desk.fillEmpty} onChange={(event) => patch({ fillEmpty: event.target.checked })} />
            Fill empty fields only
          </label>
          <p className="kicker" style={{ marginTop: "1.1rem" }}>
            Starters
          </p>
          <button
            type="button"
            className="btn-quiet block"
            style={{ marginTop: "0.55rem" }}
            onClick={() => setOrder((current) => [...current].sort(() => Math.random() - 0.5))}
          >
            <Shuffle size={16} /> Randomize starters
          </button>
          {order.map(([title, concept]) => (
            <button key={title} type="button" className="btn-quiet block" style={{ marginTop: "0.45rem" }} onClick={() => patch({ concept })}>
              {title}
            </button>
          ))}
        </section>
        <section className="slab">
          <h2>References</h2>
          <label
            className="drop"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              addFiles(event.dataTransfer.files);
            }}
          >
            <span>
              <ImagePlus size={18} style={{ margin: "0 auto 0.35rem" }} />
              <br />
              Drop pictures, or click to upload
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              multiple
              className="sr-only"
              onChange={(event) => {
                addFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </label>
          <p className="hint">They stay with this card until you remove them. A vision model can read them when you write the card. The starred one is the portrait.</p>
          {desk.references.length === 0 ? <p className="hint">No reference pictures yet.</p> : null}
          {desk.references.map((pic) => (
            <div key={pic.id} className="ref-row">
              <img src={pic.url} alt="" style={{ width: "2.2rem", height: "2.2rem", objectFit: "cover", borderRadius: "0.4rem" }} />
              <button type="button" className="name" onClick={() => star(pic)}>
                {pic.name}
              </button>
              <button type="button" className="icon-btn" aria-label="Use as portrait" onClick={() => star(pic)}>
                <Star size={16} fill={desk.starredRef === pic.id ? "currentColor" : "none"} />
              </button>
              <button
                type="button"
                className="icon-btn"
                aria-label="Remove picture"
                onClick={() => patch({ references: desk.references.filter((item) => item.id !== pic.id) })}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          <label className="check">
            <input type="checkbox" checked={desk.sendRefs} onChange={(event) => patch({ sendRefs: event.target.checked })} />
            Send pictures to the model
          </label>
        </section>
        <section className="slab">
          <h2>KoboldCPP</h2>
          <label className="field">
            <span className="kicker">OpenAI endpoint</span>
            <input value={desk.kobold} onChange={(event) => patch({ kobold: event.target.value })} placeholder="http://localhost:5001" />
          </label>
          <p className="hint">Usually http://127.0.0.1:5001/v1. The Windows app talks to Kobold on your PC. This preview can only reach it when Kobold is running on the same computer.</p>
          <label className="field">
            <span className="kicker">Password, if you set one</span>
            <input type="password" value={desk.koboldKey} onChange={(event) => patch({ koboldKey: event.target.value })} />
          </label>
          <label className="field">
            <span className="kicker">Temperature {desk.writerTemp.toFixed(2)}</span>
            <input type="range" min={0} max={2} step={0.05} value={desk.writerTemp} onChange={(event) => patch({ writerTemp: Number(event.target.value) })} />
          </label>
          <label className="field">
            <span className="kicker">Max tokens</span>
            <input type="number" min={64} max={32000} value={desk.writerMax} onChange={(event) => patch({ writerMax: Number(event.target.value) || 0 })} />
          </label>
          <button type="button" className="btn-quiet block" style={{ marginTop: "0.7rem" }} onClick={() => void testKobold()}>
            Test connection
          </button>
        </section>
        <section className="slab">
          <h2>Library</h2>
          <div className="actions">
            <button type="button" className="btn-quiet" onClick={onKeep}>
              Keep
            </button>
            <button type="button" className="btn-quiet" onClick={onNew}>
              <Plus size={16} /> New
            </button>
          </div>
          {rows.length === 0 ? <p className="hint">Nothing saved yet.</p> : null}
          {rows.map((row) => (
            <div key={row.id} className="library-row">
              <button type="button" className="name" onClick={() => onOpen(row)}>
                {row.card.name || "Unnamed"}
              </button>
              <button type="button" className="icon-btn" aria-label={`Remove ${row.card.name || "card"}`} onClick={() => onRemove(row.id)}>
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </section>
      </div>

      <div className="desk-col">
        <section className="slab">
          <div className="pair">
            <label className="field" style={{ marginTop: 0 }}>
              <span className="kicker">Name</span>
              <input value={desk.card.name} onChange={(event) => patchCard({ name: event.target.value })} />
            </label>
            <label className="field" style={{ marginTop: 0 }}>
              <span className="kicker">Summary</span>
              <input value={desk.card.summary} onChange={(event) => patchCard({ summary: event.target.value })} />
            </label>
          </div>
        </section>
        <section className="slab">
          <h2>Version</h2>
          <p className="hint">Keeping this card again saves the previous copy and raises the version.</p>
          <label className="field">
            <span className="kicker">Saved copies</span>
            <select
              className="box"
              value="current"
              onChange={(event) => {
                const snap = desk.versions.find((item) => item.id === event.target.value);
                if (snap?.card) patch({ card: snap.card, status: `Restored the ${snap.version} copy.` });
              }}
            >
              <option value="current">This card · {desk.card.character_version || "1.0"}</option>
              {desk.versions.map((snap) => (
                <option key={snap.id} value={snap.id} disabled={!snap.card}>
                  {snap.version} · {snap.note || snap.at}
                </option>
              ))}
            </select>
          </label>
        </section>
        <section className="slab">
          <h2>Creator</h2>
          <p className="hint">Who made this card. You can type a name, or use a persona.</p>
          <label className="field">
            <span className="kicker">Name</span>
            <input value={desk.card.creator} onChange={(event) => patchCard({ creator: event.target.value })} />
          </label>
          <label className="field">
            <span className="kicker">Persona</span>
            <select className="box" value={personaId} onChange={(event) => patch({ activePersona: event.target.value })}>
              <option value="">No persona selected</option>
              {desk.personas.map((row) => (
                <option key={row.id} value={row.id}>
                  Persona in the editor · {row.card.name || "Unnamed"}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn-quiet block"
            style={{ marginTop: "0.7rem" }}
            disabled={!personaId}
            onClick={() => {
              const row = desk.personas.find((item) => item.id === personaId);
              if (row) patchCard({ creator: row.card.name || desk.card.creator });
            }}
          >
            Use this persona
          </button>
        </section>
        <section className="slab">
          <h2>Chat colors</h2>
          <p className="hint">These colors travel with the card and color this character's messages. Empty dialogue uses the default. Empty box uses the sheet.</p>
          <ColorField label="Name color" value={desk.look.nameColor} placeholder="#e8b86d" onChange={(nameColor) => patch({ look: { ...desk.look, nameColor } })} />
          <ColorField label="Dialogue color" value={desk.look.dialogue} placeholder="Empty uses the Colors default" onChange={(dialogue) => patch({ look: { ...desk.look, dialogue } })} />
          <ColorField label="Box color" value={desk.look.messageBox} placeholder="Empty uses the chat paper" onChange={(messageBox) => patch({ look: { ...desk.look, messageBox } })} />
          <div className="sample" style={{ background: box, color: dialogue }}>
            <strong style={{ color: nameColor }}>{sheetName === "Unnamed" ? "Character" : sheetName}</strong>
            <p style={{ margin: 0 }}>They look over. "Stay close." *A lamp flickers.*</p>
          </div>
          <label className="field">
            <span className="kicker">Aliases</span>
            <textarea
              style={{ minHeight: "4.5rem" }}
              value={desk.card.aliases}
              placeholder="Other names, one per line. Used when you write who should answer."
              onChange={(event) => patchCard({ aliases: event.target.value })}
            />
          </label>
        </section>
        <section className="slab">
          {FIELDS.map((field) => (
            <div key={field.key} style={{ marginTop: "1.1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                <span className="kicker">{field.label}</span>
                <button type="button" className="rewrite" disabled={busy} onClick={() => onRewrite(field.key, field.label)}>
                  Rewrite
                </button>
              </div>
              <textarea
                rows={field.rows}
                value={String(desk.card[field.key] ?? "")}
                onChange={(event) => patchCard({ [field.key]: event.target.value })}
              />
              <p className="hint">
                {field.hint} · {words(String(desk.card[field.key] ?? ""))}
              </p>
            </div>
          ))}
          <label className="field">
            <span className="kicker">Tags</span>
            <input
              value={desk.card.tags.join(", ")}
              placeholder="original, slow-burn, city"
              onChange={(event) => patchCard({ tags: event.target.value.split(",").map((item) => item.trim()) })}
            />
          </label>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem" }}>
            <span className="kicker">Alternate greetings</span>
            <button
              type="button"
              className="icon-btn"
              aria-label="Add greeting"
              onClick={() => patchCard({ alternate_greetings: [...desk.card.alternate_greetings, ""] })}
            >
              <Plus size={16} />
            </button>
          </div>
          <p className="hint">The first message is greeting 1. Each box is another opening you can swipe to in chat.</p>
          {desk.card.alternate_greetings.map((greeting, index) => (
            <textarea
              key={index}
              value={greeting}
              onChange={(event) =>
                patchCard({
                  alternate_greetings: desk.card.alternate_greetings.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)),
                })
              }
            />
          ))}
          <label className="field">
            <span className="kicker">Talkativeness {desk.card.talkativeness}</span>
            <input
              type="range"
              min={0}
              max={100}
              value={desk.card.talkativeness}
              onChange={(event) => patchCard({ talkativeness: Number(event.target.value) })}
            />
          </label>
          <label className="field">
            <span className="kicker">Linked lorebook</span>
            <select className="box" value={desk.linkedBook} onChange={(event) => patch({ linkedBook: event.target.value })}>
              <option value="">None</option>
              {desk.lorebooks.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <p className="hint">{book ? `${book.name} is packed into new chats with this card.` : "New chats with this card include that lorebook. World books are chosen inside the chat."}</p>
          <div className="actions">
            <button type="button" className="btn-accent" onClick={onJson}>
              <Download size={16} /> Download JSON
            </button>
            <button type="button" className="btn-quiet" onClick={onPng}>
              <Download size={16} /> Download PNG
            </button>
            <button type="button" className="btn-quiet" onClick={onCopy}>
              <Copy size={16} /> Copy JSON
            </button>
          </div>
          <label className="btn-quiet" style={{ marginTop: "0.5rem" }}>
            <Upload size={16} /> Import
            <input type="file" accept="application/json,.json,.png" className="sr-only" onChange={(event) => onImport(event.target.files?.[0])} />
          </label>
          <p className="hint">{desk.status}</p>
        </section>
        <details className="slab">
          <summary className="kicker">More card tools</summary>
          {extras}
        </details>
      </div>

      <div className="desk-col" aria-label="Character sheet">
        <article className="sheet">
          <p className="kicker">Character sheet</p>
          <h2>{sheetName}</h2>
          <p>{desk.card.summary.trim() || "No summary yet."}</p>
          <hr className="rule" />
          {desk.card.description.trim() ? (
            <div className="prose">
              <h3>Description</h3>
              <p>{desk.card.description}</p>
            </div>
          ) : null}
          {desk.card.personality.trim() ? (
            <div className="prose">
              <h3>Personality</h3>
              <p>{desk.card.personality}</p>
            </div>
          ) : null}
          {desk.card.scenario.trim() ? (
            <div className="prose">
              <h3>Scenario</h3>
              <p>{desk.card.scenario}</p>
            </div>
          ) : null}
          {desk.card.first_mes.trim() ? (
            <div className="prose">
              <h3>First message</h3>
              <p>{desk.card.first_mes}</p>
            </div>
          ) : null}
        </article>
        <p className="hint" style={{ margin: "0.8rem 0.2rem 0" }}>
          Backstory and appearance live in Marinara's extensions. A PNG download uses the portrait and hides the same card inside the file.
        </p>
      </div>
    </div>
  );
}

function ColorField({ label, value, placeholder, onChange }: { label: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  const hex = /^#[0-9a-fA-F]{6}$/.test(value) ? value : "#e8b86d";
  return (
    <label className="field">
      <span className="kicker">{label}</span>
      <span className="swatch">
        <input type="color" value={hex} aria-label={label} onChange={(event) => onChange(event.target.value)} />
        <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
      </span>
    </label>
  );
}
