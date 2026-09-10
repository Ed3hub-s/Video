import type {Scene, SubtitleCue} from '../types';

export const secToFrames = (seconds: number, fps: number): number =>
  Math.round(seconds * fps);

export const frameToSec = (frame: number, fps: number): number => frame / fps;

export const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

export const getSubtitleForFrame = (
  cues: SubtitleCue[],
  frame: number,
  fps: number,
): SubtitleCue | undefined => {
  const now = frame / fps;
  return cues.find((cue) => now >= cue.start && now < cue.end);
};

export const sceneFrames = (scene: Scene, fps: number): number =>
  Math.max(1, secToFrames(scene.durationSeconds ?? 4, fps));

export const introPaddingSeconds = 0.3;
