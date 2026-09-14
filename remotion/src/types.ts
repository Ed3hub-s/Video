// TypeScript mirrors of the Python scene schemas.
// Scene JSON is data only.

export type Importance =
  | 'low'
  | 'medium'
  | 'high';

export type TransitionType =
  | 'fade'
  | 'slide'
  | 'wipe'
  | 'zoom';

export type ActionType =
  | 'reveal'
  | 'handwrite'
  | 'underline'
  | 'circle'
  | 'drawArrow'
  | 'drawBox'
  | 'highlight'
  | 'crossOut'
  | 'connect'
  | 'zoomFocus'
  | 'buildDiagram'
  | 'compare';

export interface KeyConcept {
  id: string;
  text: string;
  importance: Importance;
}

export interface VisualAction {
  type: ActionType;
  startSec: number;
  durationSec: number;
  target?: string | null;
  from?: string | null;
  to?: string | null;
}

export interface DiagramNode {
  id: string;
  label: string;
}

export interface DiagramEdge {
  from: string;
  to: string;
}

export interface Diagram {
  kind: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
}

export interface SubtitleCue {
  start: number;
  end: number;
  text: string;
}

export interface AudioMetadata {
  path: string;
  durationSeconds: number;
}

export interface Scene {
  id: string;
  type: string;
  title: string;
  screenText: string;
  voiceover: string;
  keyConcepts: KeyConcept[];
  visualStrategy: string;
  visualActions: VisualAction[];
  image?: string | null;
  diagram?: Diagram | null;
  audio?: AudioMetadata | null;
  subtitles: SubtitleCue[];
  durationSeconds: number | null;
  sourceText?: string;
  warnings?: string[];
}

export interface ChapterManifest {
  courseTitle: string;
  chapterNumber: number;
  chapterTitle: string;
  fps: number;
  width: number;
  height: number;
  scenes: Scene[];
  totalDurationSeconds: number;

  theme?: Partial<
    import('./theme').Theme
  >;

  style?: string;

  transition?: TransitionType;
}