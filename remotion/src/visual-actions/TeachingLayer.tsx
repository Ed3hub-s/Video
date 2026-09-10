import React from 'react';

import type {Theme} from '../theme';
import type {Scene, VisualAction} from '../types';
import {useProgress} from '../utils/animation';
import type {Rect} from '../utils/layout';

import {Compare} from './Compare';
import {Connect} from './Connect';
import {CrossOut} from './CrossOut';
import {DrawArrow} from './DrawArrow';
import {DrawBox} from './DrawBox';
import {DrawCircle} from './DrawCircle';
import {Handwrite} from './Handwrite';
import {Highlight} from './Highlight';
import {Underline} from './Underline';
import {ZoomFocus} from './ZoomFocus';

const conceptText = (scene: Scene, id?: string | null): string => {
  if (!id) {
    return '';
  }
  return scene.keyConcepts.find((concept) => concept.id === id)?.text ?? id;
};

export const TeachingLayer: React.FC<{
  scene: Scene;
  frame: number;
  fps: number;
  theme: Theme;
  conceptRects: Map<string, Rect>;
  diagramRects: Map<string, Rect>;
}> = ({scene, frame, fps, theme, conceptRects, diagramRects}) => {
  const rectFor = (id?: string | null): Rect | undefined => {
    if (!id) {
      return undefined;
    }
    return conceptRects.get(id) ?? diagramRects.get(id);
  };

  return (
    <>
      {scene.visualActions.map((action, index) => {
        const progress = useProgress(frame, action.startSec, action.durationSec, fps);
        const target = rectFor(action.target);
        const key = `${action.type}-${action.startSec}-${index}`;
        switch (action.type) {
          case 'reveal':
          case 'buildDiagram':
            return null;
          case 'underline':
            return target ? <Underline key={key} rect={target} progress={progress} color={theme.accent} /> : null;
          case 'circle':
            return target ? <DrawCircle key={key} rect={target} progress={progress} color={theme.accent} /> : null;
          case 'drawBox':
            return target ? <DrawBox key={key} rect={target} progress={progress} color={theme.accent} /> : null;
          case 'highlight':
            return target ? <Highlight key={key} rect={target} progress={progress} color="#FFD54A" /> : null;
          case 'crossOut':
            return target ? <CrossOut key={key} rect={target} progress={progress} color="#D32F2F" /> : null;
          case 'handwrite':
            return target ? (
              <Handwrite
                key={key}
                rect={target}
                text={conceptText(scene, action.target)}
                progress={progress}
                color={theme.accent}
              />
            ) : null;
          case 'drawArrow':
          case 'connect': {
            const from = rectFor(action.from);
            const to = rectFor(action.to);
            if (!from || !to) {
              return null;
            }
            return action.type === 'drawArrow' ? (
              <DrawArrow key={key} fromRect={from} toRect={to} progress={progress} color={theme.accent} />
            ) : (
              <Connect key={key} fromRect={from} toRect={to} progress={progress} color={theme.accent} />
            );
          }
          case 'zoomFocus':
            return target ? <ZoomFocus key={key} rect={target} progress={progress} /> : null;
          case 'compare': {
            const left = scene.keyConcepts[0] ? rectFor(scene.keyConcepts[0].id) : undefined;
            const right = scene.keyConcepts[1] ? rectFor(scene.keyConcepts[1].id) : undefined;
            if (!left || !right) {
              return null;
            }
            return (
              <Compare
                key={key}
                leftRect={left}
                rightRect={right}
                leftText={conceptText(scene, scene.keyConcepts[0]?.id)}
                rightText={conceptText(scene, scene.keyConcepts[1]?.id)}
                progress={progress}
                color={theme.accent}
              />
            );
          }
          default:
            return null;
        }
      })}
    </>
  );
};

export type {VisualAction};
