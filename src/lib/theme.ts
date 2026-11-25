export type AppTheme = {
  bg: string;
  surface: string;
  inset: string;
  fg: string;
  muted: string;
  line: string;
  accent: string;
  accentInk: string;
  paper: string;
  ink: string;
  gold: string;
  radius: number;
  buttonRadius: number;
  size: number;
  font: "cardwright" | "system" | "serif" | "mono" | "custom";
  customFont: string;
  extraCss: string;
};

export const themeFields = [
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
  ["gold", "Sheet rule"],
] as const;

const KEY = "redwright-theme";

export const cardwrightTheme: AppTheme = {
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
  extraCss: "",
};

export const themePresets: { name: string; theme: AppTheme }[] = [
  { name: "Cardwright", theme: cardwrightTheme },
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
      buttonRadius: 10,
    },
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
      radius: 18,
    },
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
      gold: "#8eb6ff",
    },
  },
];

function stacks(theme: AppTheme) {
  if (theme.font === "custom" && theme.customFont.trim()) {
    const family = theme.customFont.trim().replace(/[;{}]/g, "");
    return { ui: family, display: family };
  }
  if (theme.font === "system") return { ui: '"Segoe UI", sans-serif', display: "Palatino, Georgia, serif" };
  if (theme.font === "serif") return { ui: 'Georgia, "Iowan Old Style", serif', display: 'Georgia, "Iowan Old Style", serif' };
  if (theme.font === "mono") return { ui: 'ui-monospace, "Cascadia Code", monospace', display: "ui-monospace, monospace" };
  return { ui: '"Outfit", "Avenir Next", "Segoe UI", sans-serif', display: '"Fraunces", "Iowan Old Style", Palatino, serif' };
}

export function applyTheme(theme: AppTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const font = stacks(theme);
  const values: Record<string, string> = {
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
    "--font-display": font.display,
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

export function loadTheme(): AppTheme {
  if (typeof window === "undefined") return cardwrightTheme;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return cardwrightTheme;
    const parsed = JSON.parse(raw) as Partial<AppTheme>;
    return { ...cardwrightTheme, ...parsed };
  } catch {
    return cardwrightTheme;
  }
}

export function saveTheme(theme: AppTheme) {
  localStorage.setItem(KEY, JSON.stringify(theme));
}
