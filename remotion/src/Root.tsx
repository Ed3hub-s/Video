import React from 'react';
import {Composition} from 'remotion';

import {Tutorial} from './Tutorial';
import {TestSuite} from './TestSuite';
import type {ChapterManifest} from './types';

const DEFAULT_MANIFEST: ChapterManifest = {
  courseTitle: 'Course Video Generator',
  chapterNumber: 0,
  chapterTitle: 'Demo',
  fps: 30,
  width: 1920,
  height: 1080,
  scenes: [],
  totalDurationSeconds: 0,
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Tutorial"
      component={Tutorial}
      durationInFrames={1}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{manifest: DEFAULT_MANIFEST}}
      calculateMetadata={({props}) => {
        const manifest = (props.manifest ?? DEFAULT_MANIFEST) as ChapterManifest;
        const fps = manifest.fps || 30;
        const frames = manifest.scenes.reduce(
          (sum, scene) => sum + Math.max(1, Math.round((scene.durationSeconds ?? 4) * fps)),
          0,
        );
        return {
          durationInFrames: Math.max(1, frames),
          fps,
          width: manifest.width || 1920,
          height: manifest.height || 1080,
        };
      }}
    />
    <Composition
      id="TestSuite"
      component={TestSuite}
      durationInFrames={480}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
