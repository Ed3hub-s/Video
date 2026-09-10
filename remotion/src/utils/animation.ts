import {interpolate} from 'remotion';

import {clamp} from './timing';

export const easeInOut = (t: number): number =>
  t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

export const useProgress = (
  frame: number,
  startSec: number,
  durationSec: number,
  fps: number,
): number => {
  const start = startSec * fps;
  const end = start + Math.max(1, durationSec * fps);
  return easeInOut(
    clamp(interpolate(frame, [start, end], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }), 0, 1),
  );
};

export const fadeIn = (
  frame: number,
  startSec: number,
  durationSec: number,
  fps: number,
): number => useProgress(frame, startSec, durationSec, fps);

export const drawStrokeProps = (progress: number) => ({
  pathLength: 1,
  strokeDasharray: 1,
  strokeDashoffset: 1 - progress,
});

export const scaleIn = (
  frame: number,
  startSec: number,
  durationSec: number,
  fps: number,
): number => {
  const raw = useProgress(frame, startSec, durationSec, fps);
  return 0.7 + 0.3 * raw;
};
