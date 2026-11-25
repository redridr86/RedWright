import { themeFields, themePresets, type AppTheme } from "@/lib/theme";

export function ThemePanel({ theme, onChange }: { theme: AppTheme; onChange: (theme: AppTheme) => void }) {
  function set<K extends keyof AppTheme>(key: K, value: AppTheme[K]) {
    onChange({ ...theme, [key]: value });
  }

  function copy() {
    void navigator.clipboard?.writeText(JSON.stringify(theme, null, 2));
  }

  function read(file: File | undefined) {
    if (!file) return;
    file
      .text()
      .then((text) => onChange({ ...theme, ...(JSON.parse(text) as Partial<AppTheme>) }))
      .catch(() => undefined);
  }

  return (
    <div className="pane">
      <div className="slab">
        <p className="kicker">Theme</p>
        <h2>App theme</h2>
        <p className="hint">Every color, the type, and the shape apply to the whole studio. The character sheet uses the paper colors.</p>
        <div className="actions">
          {themePresets.map((preset) => (
            <button key={preset.name} type="button" className="btn-quiet" onClick={() => onChange({ ...preset.theme, extraCss: theme.extraCss })}>
              {preset.name}
            </button>
          ))}
        </div>
      </div>
      <div className="slab">
        <p className="kicker">Colors</p>
        <div className="theme-grid">
          {themeFields.map(([key, label]) => (
            <label key={key} className="field">
              {label}
              <span className="swatch">
                <input
                  type="color"
                  value={/^#[0-9a-fA-F]{6}$/.test(theme[key]) ? theme[key] : "#000000"}
                  onChange={(event) => set(key, event.target.value)}
                  aria-label={label}
                />
                <input value={theme[key]} onChange={(event) => set(key, event.target.value)} />
              </span>
            </label>
          ))}
        </div>
      </div>
      <div className="slab">
        <p className="kicker">Type and shape</p>
        <label className="field">
          Font
          <select className="box" value={theme.font} onChange={(event) => set("font", event.target.value as AppTheme["font"])}>
            <option value="cardwright">Outfit and Fraunces</option>
            <option value="system">System</option>
            <option value="serif">Serif</option>
            <option value="mono">Mono</option>
            <option value="custom">Custom family</option>
          </select>
        </label>
        {theme.font === "custom" ? (
          <label className="field">
            Font family
            <input value={theme.customFont} placeholder="Georgia, serif" onChange={(event) => set("customFont", event.target.value)} />
          </label>
        ) : null}
        <label className="field">
          Text size {theme.size}
          <input type="range" min={13} max={20} value={theme.size} onChange={(event) => set("size", Number(event.target.value))} />
        </label>
        <label className="field">
          Panel corners {theme.radius}
          <input type="range" min={0} max={32} value={theme.radius} onChange={(event) => set("radius", Number(event.target.value))} />
        </label>
        <label className="field">
          Button corners {theme.buttonRadius}
          <input type="range" min={0} max={999} value={theme.buttonRadius} onChange={(event) => set("buttonRadius", Number(event.target.value))} />
        </label>
      </div>
      <div className="slab">
        <p className="kicker">Your CSS</p>
        <p className="hint">Optional rules on top of the colors. They stay on this computer.</p>
        <textarea className="inset" value={theme.extraCss} placeholder={".slab { box-shadow: none; }"} onChange={(event) => set("extraCss", event.target.value)} />
        <div className="actions">
          <button type="button" className="btn-accent" onClick={() => onChange({ ...themePresets[0].theme })}>
            Reset
          </button>
          <button type="button" className="btn-quiet" onClick={copy}>
            Copy JSON
          </button>
          <label className="btn-quiet">
            Import
            <input type="file" accept="application/json,.json" className="sr-only" onChange={(event) => read(event.target.files?.[0])} />
          </label>
        </div>
      </div>
      <div className="slab">
        <p className="kicker">Preview</p>
        <article className="sheet">
          <p className="kicker">Character sheet</p>
          <h2>Unnamed</h2>
          <p>No summary yet.</p>
          <hr className="rule" />
        </article>
        <button type="button" className="btn-accent" style={{ marginTop: "0.8rem" }}>
          Write the card
        </button>
      </div>
    </div>
  );
}
