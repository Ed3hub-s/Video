import React from 'react';

import type {Theme} from '../theme';
import type {KeyConcept} from '../types';
import type {Rect} from '../utils/layout';

import {ConceptLabel} from './ConceptLabel';

export const ConceptStrip: React.FC<{
  concepts: KeyConcept[];
  rects: Rect[];
  theme: Theme;
  revealMap: Map<string, number>;
  handwrittenIds: Set<string>;
}> = ({concepts, rects, theme, revealMap, handwrittenIds}) => {
  const byId = new Map(rects.map((rect) => [rect.id, rect]));
  return (
    <>
      {concepts.map((concept) => {
        const rect = byId.get(concept.id);
        if (!rect) {
          return null;
        }
        return (
          <ConceptLabel
            key={concept.id}
            concept={concept}
            rect={rect}
            theme={theme}
            revealProgress={revealMap.get(concept.id) ?? 1}
            handwriting={handwrittenIds.has(concept.id)}
          />
        );
      })}
    </>
  );
};
