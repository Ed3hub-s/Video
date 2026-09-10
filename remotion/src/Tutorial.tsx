import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

import {Logo} from './components/Logo';
import {ProgressBar} from './components/ProgressBar';
import {SceneContainer} from './components/SceneContainer';
import {Subtitle} from './components/Subtitle';
import {BulletList} from './scenes/BulletList';
import {ChapterIntro} from './scenes/ChapterIntro';
import {ChapterSummary} from './scenes/ChapterSummary';
import {Definition} from './scenes/Definition';
import {Explanation} from './scenes/Explanation';
import {ImageExplanation} from './scenes/ImageExplanation';
import {SectionIntro} from './scenes/SectionIntro';
import {VisualExplanation} from './scenes/VisualExplanation';
import {mergeTheme, type Theme} from './theme';
import {resolveStyle, type StylePreset} from './styles';
import type {ChapterManifest, Scene} from './types';
import {useProgress} from './utils/animation';
import {layoutConceptChips} from './utils/layout';
import {resolveMedia} from './utils/media';
import {getSubtitleForFrame, introPaddingSeconds, sceneFrames, secToFrames} from './utils/timing';
import {TeachingLayer} from './visual-actions/TeachingLayer';

const EMPTY_MANIFEST: ChapterManifest = {
  courseTitle: 'Course Video Generator',
  chapterNumber: 0,
  chapterTitle: 'Demo',
  fps: 30,
  width: 1920,
  height: 1080,
  scenes: [],
  totalDurationSeconds: 0,
};

const SceneView: React.FC<{
  scene: Scene;
  fps: number;
  theme: Theme;
  index: number;
  total: number;
  courseTitle: string;
  style: StylePreset;
}> = ({scene, fps, theme, index, total, courseTitle, style}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();

  const conceptRects = layoutConceptChips(scene.keyConcepts, width, 830);
  const conceptRectMap = new Map(conceptRects.map((rect) => [rect.id, rect]));
  const revealMap = new Map<string, number>();
  for (const action of scene.visualActions) {
    if (action.type === 'reveal' && action.target) {
      const progress = useProgress(frame, action.startSec, action.durationSec, fps);
      revealMap.set(action.target, Math.max(revealMap.get(action.target) ?? 0, progress));
    }
  }
  const handwrittenIds = new Set(
    scene.visualActions
      .filter(
        (action) =>
          action.type === 'handwrite' &&
          action.target &&
          useProgress(frame, action.startSec, action.durationSec, fps) > 0.4,
      )
      .map((action) => action.target as string),
  );

  const sceneProps = {
    scene,
    frame,
    fps,
    theme,
    conceptRects,
    revealMap,
    handwrittenIds,
    index,
    total,
  };

  let body: React.ReactNode;
  switch (scene.type) {
    case 'chapterIntro':
      body = <ChapterIntro {...sceneProps} />;
      break;
    case 'sectionIntro':
      body = <SectionIntro {...sceneProps} />;
      break;
    case 'definition':
      body = <Definition {...sceneProps} />;
      break;
    case 'bulletList':
      body = <BulletList {...sceneProps} />;
      break;
    case 'imageExplanation':
      body = <ImageExplanation {...sceneProps} />;
      break;
    case 'visualExplanation':
      body = <VisualExplanation {...sceneProps} />;
      break;
    case 'chapterSummary':
      body = <ChapterSummary {...sceneProps} />;
      break;
    case 'explanation':
    default:
      body = <Explanation {...sceneProps} />;
      break;
  }

  const cue = getSubtitleForFrame(scene.subtitles, frame, fps);
  return (
    <SceneContainer theme={theme} background={style.background}>
      <Logo theme={theme} courseTitle={courseTitle} />
      {style.watermark ? (
        <div
          style={{
            position: 'absolute',
            right: theme.safeMarginX,
            bottom: 42,
            fontSize: 20,
            fontWeight: 700,
            letterSpacing: 4,
            color: theme.muted,
            opacity: 0.75,
          }}
        >
          {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}
        </div>
      ) : null}
      {body}
      {scene.audio ? (
        <Sequence from={secToFrames(introPaddingSeconds, fps)}>
          <Audio src={resolveMedia(scene.audio.path)} />
        </Sequence>
      ) : null}
      <TeachingLayer
        scene={scene}
        frame={frame}
        fps={fps}
        theme={theme}
        conceptRects={conceptRectMap}
        diagramRects={new Map()}
      />
      <Subtitle cue={cue} frame={frame} fps={fps} theme={theme} variant={style.subtitle} />
    </SceneContainer>
  );
};

const ChapterProgress: React.FC<{totalFrames: number; theme: Theme}> = ({totalFrames, theme}) => {
  const frame = useCurrentFrame();
  return <ProgressBar frame={frame} totalFrames={totalFrames} theme={theme} />;
};

const SceneFade: React.FC<{
  fadeFrames: number;
  sceneFrames: number;
  children: React.ReactNode;
}> = ({fadeFrames, sceneFrames, children}) => {
  const frame = useCurrentFrame();
  const fade = Math.max(1, Math.min(fadeFrames, Math.floor(sceneFrames / 4)));
  const opacity = interpolate(
    frame,
    [0, fade, sceneFrames - fade, sceneFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return <div style={{position: 'absolute', inset: 0, opacity}}>{children}</div>;
};

export const Tutorial: React.FC<{manifest?: ChapterManifest}> = ({manifest}) => {
  const data = manifest ?? EMPTY_MANIFEST;
  const preset = resolveStyle(data.style);
  const theme = mergeTheme({...preset.theme, ...(data.theme ?? {})});
  const fps = data.fps || 30;
  const segments = data.scenes.map((scene) => {
    const frames = sceneFrames(scene, fps);
    return {scene, frames};
  });
  let cursor = 0;
  const totalFrames = segments.reduce((sum, segment) => sum + segment.frames, 0);

  return (
    <AbsoluteFill>
      {segments.map(({scene, frames}, index) => {
        const start = cursor;
        cursor += frames;
        return (
          <Sequence key={scene.id} from={start} durationInFrames={frames}>
            <SceneFade fadeFrames={preset.transitionFrames} sceneFrames={frames}>
              <SceneView
                scene={scene}
                fps={fps}
                theme={theme}
                index={index}
                total={data.scenes.length}
                courseTitle={data.courseTitle}
                style={preset}
              />
            </SceneFade>
          </Sequence>
        );
      })}
      <ChapterProgress totalFrames={Math.max(1, totalFrames)} theme={theme} />
    </AbsoluteFill>
  );
};
