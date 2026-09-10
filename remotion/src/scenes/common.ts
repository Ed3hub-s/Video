import type {Theme} from '../theme';
import type {Scene} from '../types';
import type {Rect} from '../utils/layout';

export interface SceneProps {
  scene: Scene;
  frame: number;
  fps: number;
  theme: Theme;
  conceptRects: Rect[];
  revealMap: Map<string, number>;
  handwrittenIds: Set<string>;
  index: number;
  total: number;
}
