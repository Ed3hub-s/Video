import type {Theme} from './theme';

export type BackgroundTreatment = 'flat' | 'soft' | 'dark-glow' | 'sunset' | 'paper';
export type SubtitleVariant = 'pill' | 'bar';

export interface StylePreset {
  name: string;
  label: string;
  theme: Partial<Theme>;
  background: BackgroundTreatment;
  subtitle: SubtitleVariant;
  transitionFrames: number;
  watermark: boolean;
  description: string;
}

export const stylePresets: Record<string, StylePreset> = {
  studio: {
    name: 'studio',
    label: 'Studio',
    theme: {},
    background: 'soft',
    subtitle: 'pill',
    transitionFrames: 10,
    watermark: false,
    description: 'Light, clean, orange accent - the V1 default look.',
  },
  dark: {
    name: 'dark',
    label: 'Dark',
    theme: {
      background: '#10151A',
      foreground: '#F2F6F9',
      muted: '#93A3B0',
      accent: '#4CC9F0',
      borderRadius: 18,
    },
    background: 'dark-glow',
    subtitle: 'bar',
    transitionFrames: 12,
    watermark: true,
    description: 'Deep navy-black with a cyan accent - modern and focused.',
  },
  playful: {
    name: 'playful',
    label: 'Playful',
    theme: {
      background: '#FFF7E8',
      foreground: '#2B2118',
      muted: '#8A7460',
      accent: '#FF6B35',
      borderRadius: 30,
    },
    background: 'sunset',
    subtitle: 'pill',
    transitionFrames: 12,
    watermark: false,
    description: 'Warm pastels, rounded corners, bold and friendly.',
  },
  minimal: {
    name: 'minimal',
    label: 'Minimal',
    theme: {
      background: '#FAFAFA',
      foreground: '#111111',
      muted: '#777777',
      accent: '#111111',
      fontFamily: "'Georgia', 'Times New Roman', serif",
      borderRadius: 10,
    },
    background: 'flat',
    subtitle: 'pill',
    transitionFrames: 6,
    watermark: false,
    description: 'Black and white, serif headings, one strong accent.',
  },
  cinema: {
    name: 'cinema',
    label: 'Cinema',
    theme: {
      background: '#0C0A08',
      foreground: '#F6F0E4',
      muted: '#B9AE99',
      accent: '#E3B25B',
      borderRadius: 20,
      fontFamily: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    },
    background: 'dark-glow',
    subtitle: 'bar',
    transitionFrames: 16,
    watermark: true,
    description: 'Warm black with gold accents - premium and cinematic.',
  },
};

export const styleNames = Object.keys(stylePresets);

export const resolveStyle = (name?: string): StylePreset =>
  stylePresets[name ?? 'studio'] ?? stylePresets.studio;
