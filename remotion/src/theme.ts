// Single source of truth for brand styling on the Remotion side.
// Changing brand identity means editing this file (and mirroring branding in
// pipeline/config.py when the Python side needs to know it).

export interface Theme {
  background: string;
  foreground: string;
  muted: string;
  accent: string;
  fontFamily: string;
  titleSize: number;
  headingSize: number;
  bodySize: number;
  subtitleSize: number;
  spacing: number;
  borderRadius: number;
  safeMarginX: number;
  safeMarginY: number;
}

export const theme: Theme = {
  background: '#F5F5F5',
  foreground: '#111111',
  muted: '#6B6B6B',
  accent: '#FF5A36',
  fontFamily: "Inter, 'Segoe UI', Arial, sans-serif",
  titleSize: 88,
  headingSize: 56,
  bodySize: 38,
  subtitleSize: 32,
  spacing: 48,
  borderRadius: 24,
  safeMarginX: 120,
  safeMarginY: 80,
};

export const mergeTheme = (partial?: Partial<Theme>): Theme => ({
  ...theme,
  ...(partial ?? {}),
});
