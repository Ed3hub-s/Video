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
import {
  getSubtitleForFrame,
  introPaddingSeconds,
  sceneFrames,
  secToFrames,
} from './utils/timing';

type TransitionType = 'fade' | 'slide' | 'wipe' | 'zoom';

type ManifestWithTransition = ChapterManifest & {
  transition?: TransitionType;
};

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

const resolveTransition = (value?: string): TransitionType => {
  switch (value) {
    case 'fade':
    case 'slide':
    case 'wipe':
    case 'zoom':
      return value;
    default:
      return 'fade';
  }
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

  const revealMap = new Map<string, number>();
  for (const action of scene.visualActions) {
    if (action.type === 'reveal' && action.target) {
      const progress = useProgress(
        frame,
        action.startSec,
        action.durationSec,
        fps,
      );

      revealMap.set(
        action.target,
        Math.max(revealMap.get(action.target) ?? 0, progress),
      );
    }
  }

  const handwrittenIds = new Set(
    scene.visualActions
      .filter(
        (action) =>
          action.type === 'handwrite' &&
          action.target &&
          useProgress(
            frame,
            action.startSec,
            action.durationSec,
            fps,
          ) > 0.4,
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

  const immediateNarration =
    scene.type === 'chapterIntro' || scene.type === 'sectionIntro';

  const normalAudioDelayFrames = secToFrames(
    introPaddingSeconds,
    fps,
  );

  const audioStartFrame = immediateNarration
    ? 0
    : normalAudioDelayFrames;

  const subtitleLookupFrame = immediateNarration
    ? frame + normalAudioDelayFrames
    : frame;

  const cue = getSubtitleForFrame(
    scene.subtitles,
    subtitleLookupFrame,
    fps,
  );

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
          {String(index + 1).padStart(2, '0')} /{' '}
          {String(total).padStart(2, '0')}
        </div>
      ) : null}

      {body}

      {scene.audio ? (
        audioStartFrame > 0 ? (
          <Sequence from={audioStartFrame}>
            <Audio src={resolveMedia(scene.audio.path)} />
          </Sequence>
        ) : (
          <Audio src={resolveMedia(scene.audio.path)} />
        )
      ) : null}

      <Subtitle
        cue={cue}
        frame={subtitleLookupFrame}
        fps={fps}
        theme={theme}
        variant={style.subtitle}
      />
    </SceneContainer>
  );
};

const ChapterProgress: React.FC<{
  totalFrames: number;
  theme: Theme;
}> = ({totalFrames, theme}) => {
  const frame = useCurrentFrame();

  return (
    <ProgressBar
      frame={frame}
      totalFrames={totalFrames}
      theme={theme}
    />
  );
};

const SceneTransition: React.FC<{
  type: TransitionType;
  transitionFrames: number;
  sceneFrames: number;
  index: number;
  children: React.ReactNode;
}> = ({
  type,
  transitionFrames,
  sceneFrames,
  index,
  children,
}) => {
  const frame = useCurrentFrame();

  if (index === 0) {
    return (
      <div style={{position: 'absolute', inset: 0}}>
        {children}
      </div>
    );
  }

  const duration = Math.max(
    1,
    Math.min(
      transitionFrames,
      Math.floor(sceneFrames / 4),
    ),
  );

  const progress = interpolate(
    frame,
    [0, duration],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    },
  );

  const transitionStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    transformOrigin: 'center center',
  };

  switch (type) {
    case 'fade':
      transitionStyle.opacity = interpolate(
        progress,
        [0, 1],
        [0.45, 1],
      );
      break;

    case 'slide': {
      const direction = index % 2 === 0 ? 1 : -1;

      const offset =
        direction *
        interpolate(
          progress,
          [0, 1],
          [54, 0],
        );

      transitionStyle.opacity = interpolate(
        progress,
        [0, 1],
        [0.7, 1],
      );

      transitionStyle.transform = `translateX(${offset}px)`;
      break;
    }

    case 'wipe': {
      const hidden = interpolate(
        progress,
        [0, 1],
        [100, 0],
      );

      transitionStyle.clipPath = `inset(0 ${hidden}% 0 0)`;
      break;
    }

    case 'zoom': {
      const scale = interpolate(
        progress,
        [0, 1],
        [1.035, 1],
      );

      transitionStyle.opacity = interpolate(
        progress,
        [0, 1],
        [0.55, 1],
      );

      transitionStyle.transform = `scale(${scale})`;
      break;
    }

    default:
      break;
  }

  return (
    <div style={transitionStyle}>
      {children}
    </div>
  );
};

export const Tutorial: React.FC<{
  manifest?: ChapterManifest;
}> = ({manifest}) => {
  const data = manifest ?? EMPTY_MANIFEST;
  const preset = resolveStyle(data.style);
  const theme = mergeTheme({
    ...preset.theme,
    ...(data.theme ?? {}),
  });

  const fps = data.fps || 30;

  const transition = resolveTransition(
    (data as ManifestWithTransition).transition,
  );

  const segments = data.scenes.map((scene) => {
    const frames = sceneFrames(scene, fps);
    return {scene, frames};
  });

  let cursor = 0;

  const totalFrames = segments.reduce(
    (sum, segment) => sum + segment.frames,
    0,
  );

  return (
    <AbsoluteFill>
      {segments.map(({scene, frames}, index) => {
        const start = cursor;
        cursor += frames;

        return (
          <Sequence
            key={scene.id}
            from={start}
            durationInFrames={frames}
          >
            <SceneTransition
              type={transition}
              transitionFrames={preset.transitionFrames}
              sceneFrames={frames}
              index={index}
            >
              <SceneView
                scene={scene}
                fps={fps}
                theme={theme}
                index={index}
                total={data.scenes.length}
                courseTitle={data.courseTitle}
                style={preset}
              />
            </SceneTransition>
          </Sequence>
        );
      })}

      <ChapterProgress
        totalFrames={Math.max(1, totalFrames)}
        theme={theme}
      />
    </AbsoluteFill>
  );
};
