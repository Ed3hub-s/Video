import type {Diagram, DiagramNode, KeyConcept} from '../types';

export interface Rect {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Point {
  x: number;
  y: number;
}

const textWidth = (text: string, fontSize: number): number =>
  Math.max(60, text.length * fontSize * 0.62);

export const layoutConceptChips = (
  concepts: KeyConcept[],
  width: number,
  y: number,
  fontSize = 26,
): Rect[] => {
  const chips: {w: number; h: number}[] = concepts.map((concept) => ({
    w: Math.min(480, textWidth(concept.text, fontSize) + 56),
    h: 64,
  }));
  const gap = 28;
  const total = chips.reduce((sum, chip) => sum + chip.w, 0) + gap * (chips.length - 1);
  let x = (width - total) / 2;
  return concepts.map((concept, index) => {
    const chip = chips[index];
    const rect = {id: concept.id, x, y, w: chip.w, h: chip.h};
    x += chip.w + gap;
    return rect;
  });
};

export const layoutDiagram = (
  diagram: Diagram,
  width: number,
  height: number,
): {nodes: Map<string, Point>; rects: Map<string, {x: number; y: number; w: number; h: number}>} => {
  const nodeSize = 230;
  const gap = 120;
  const positions = new Map<string, Point>();
  const rects = new Map<string, {x: number; y: number; w: number; h: number}>();
  const count = diagram.nodes.length;

  const place = (index: number, x: number, y: number): void => {
    const node = diagram.nodes[index];
    if (!node) {
      return;
    }
    positions.set(node.id, {x, y});
    rects.set(node.id, {x: x - nodeSize / 2, y: y - nodeSize / 2, w: nodeSize, h: nodeSize});
  };

  if (diagram.kind === 'comparison') {
    const mid = height / 2;
    place(0, width * 0.32, mid);
    place(1, width * 0.68, mid);
  } else if (diagram.kind === 'relationship' && count >= 3) {
    place(0, width * 0.3, height * 0.3);
    place(1, width * 0.5, height * 0.72);
    place(2, width * 0.7, height * 0.3);
    for (let i = 3; i < count; i++) {
      place(i, width * 0.5, height * (0.2 + 0.15 * i));
    }
  } else {
    const total = count * nodeSize + (count - 1) * gap;
    let x = (width - total) / 2 + nodeSize / 2;
    const y = height / 2;
    diagram.nodes.forEach((node, index) => {
      place(index, x, y);
      x += nodeSize + gap;
    });
  }
  return {nodes: positions, rects};
};

export const edgePoints = (
  diagram: Diagram,
  positions: Map<string, Point>,
): {from: Point; to: Point}[] =>
  diagram.edges
    .map((edge) => ({
      from: positions.get(edge.from),
      to: positions.get(edge.to),
    }))
    .filter(
      (pair): pair is {from: Point; to: Point} => Boolean(pair.from && pair.to),
    );

export const centerOf = (rect: {x: number; y: number; w: number; h: number}): Point => ({
  x: rect.x + rect.w / 2,
  y: rect.y + rect.h / 2,
});

export const fitFontSize = (
  text: string,
  maxWidth: number,
  baseSize: number,
  minSize = 18,
): number => {
  if (typeof document === 'undefined') {
    return baseSize;
  }
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return baseSize;
  }
  let size = baseSize;
  ctx.font = `600 ${size}px sans-serif`;
  while (size > minSize && ctx.measureText(text).width > maxWidth) {
    size -= 2;
    ctx.font = `600 ${size}px sans-serif`;
  }
  return size;
};
