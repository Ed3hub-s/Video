import React from 'react';
import {useCurrentFrame} from 'remotion';

import type {Theme} from '../theme';
import type {Diagram as DiagramData, VisualAction} from '../types';
import {useProgress} from '../utils/animation';
import {drawStrokeProps} from '../utils/animation';
import {edgePoints, layoutDiagram, type Point} from '../utils/layout';

const nodeProgress = (
  actions: VisualAction[],
  id: string,
  frame: number,
  fps: number,
): number => {
  const reveal = actions.find((action) => action.type === 'reveal' && action.target === id);
  if (reveal) {
    return useProgress(frame, reveal.startSec, reveal.durationSec, fps);
  }
  const build = actions.find((action) => action.type === 'buildDiagram');
  if (build) {
    const index = actions.indexOf(build);
    return useProgress(frame, build.startSec + index * 0.35, build.durationSec, fps);
  }
  return 1;
};

const edgeProgress = (
  actions: VisualAction[],
  from: string,
  to: string,
  frame: number,
  fps: number,
): number => {
  const arrow = actions.find(
    (action) => action.type === 'drawArrow' && action.from === from && action.to === to,
  );
  if (arrow) {
    return useProgress(frame, arrow.startSec, arrow.durationSec, fps);
  }
  const build = actions.find((action) => action.type === 'buildDiagram');
  if (build) {
    return useProgress(frame, build.startSec + 1.2, build.durationSec, fps);
  }
  return 1;
};

export const Diagram: React.FC<{
  diagram: DiagramData;
  fps: number;
  theme: Theme;
  actions: VisualAction[];
}> = ({diagram, fps, theme, actions}) => {
  const frame = useCurrentFrame();
  const {nodes, rects} = layoutDiagram(diagram, 1920, 780);
  const points = edgePoints(diagram, nodes);

  return (
    <div style={{position: 'absolute', inset: 0}}>
      <svg width={1920} height={780} style={{position: 'absolute', inset: 0}}>
        {diagram.edges.map((edge, index) => {
          const from = nodes.get(edge.from);
          const to = nodes.get(edge.to);
          if (!from || !to) {
            return null;
          }
          const progress = edgeProgress(actions, edge.from, edge.to, frame, fps);
          const dx = to.x - from.x;
          const dy = to.y - from.y;
          const length = Math.sqrt(dx * dx + dy * dy) || 1;
          const head = 28;
          const angle = Math.atan2(dy, dx);
          const endX = from.x + dx * (0.78 + 0.22 * progress);
          const endY = from.y + dy * (0.78 + 0.22 * progress);
          const tipX = from.x + (length - head) * (dx / length);
          const tipY = from.y + (length - head) * (dy / length);
          const label = `${diagram.kind}-${index}`;
          return (
            <g key={label}>
              <line
                x1={from.x}
                y1={from.y}
                x2={endX}
                y2={endY}
                stroke={theme.accent}
                strokeWidth={7}
                strokeLinecap="round"
                {...drawStrokeProps(progress)}
              />
              <polygon
                points={`${tipX},${tipY} ${tipX - head * Math.cos(angle - 0.45)},${
                  tipY - head * Math.sin(angle - 0.45)
                } ${tipX - head * Math.cos(angle + 0.45)},${
                  tipY - head * Math.sin(angle + 0.45)
                }`}
                fill={theme.accent}
                opacity={Math.min(1, Math.max(0, (progress - 0.82) * 5))}
              />
            </g>
          );
        })}
      </svg>

      {diagram.nodes.map((node) => {
        const rect = rects.get(node.id);
        const progress = nodeProgress(actions, node.id, frame, fps);
        if (!rect) {
          return null;
        }
        return (
          <div
            key={node.id}
            style={{
              position: 'absolute',
              left: rect.x,
              top: rect.y,
              width: rect.w,
              height: rect.h,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: theme.borderRadius,
              border: `4px solid ${theme.accent}`,
              backgroundColor: 'rgba(255,255,255,0.85)',
              fontSize: 34,
              fontWeight: 800,
              color: theme.foreground,
              opacity: progress,
              transform: `scale(${0.8 + 0.2 * progress})`,
              boxShadow: '0 18px 50px rgba(17,17,17,0.12)',
            }}
          >
            {node.label}
          </div>
        );
      })}
    </div>
  );
};

export type {Point};
