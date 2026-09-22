import { Component, computed, input } from '@angular/core';

/* Pixel art as data, not image files.

   Each sprite is a grid of strings, '#' = filled. We render one <rect> per
   filled cell into a viewBox sized to the grid, so the sprite scales to any
   size without blurring and takes its colour from CSS `currentColor`.
   Editing a dinosaur means editing ASCII below. */

const SPRITES = {
  trex: [
    '........######..',
    '.......########.',
    '.......##.#####.',
    '.......########.',
    '.......#######..',
    '.......######...',
    '#......######...',
    '##....########..',
    '###..##########.',
    '################',
    '.###############',
    '..#############.',
    '...####..#####..',
    '...###....####..',
    '...##......###..',
    '...##......##...',
  ],
  sauropod: [
    '..........####..',
    '.........######.',
    '.........##.###.',
    '.........######.',
    '..........####..',
    '..........###...',
    '..........###...',
    '..........###...',
    '.......######...',
    '....############',
    '..##############',
    '.###############',
    '.###############',
    '..####....####..',
    '..###......###..',
    '..##.......###..',
  ],
  egg: [
    '.....######.....',
    '...##########...',
    '..############..',
    '.##############.',
    '.##############.',
    '################',
    '################',
    '################',
    '################',
    '################',
    '.##############.',
    '.##############.',
    '..############..',
    '...##########...',
    '.....######.....',
    '................',
  ],
} as const;

export type SpriteName = keyof typeof SPRITES;

@Component({
  selector: 'pixel-dino',
  template: `
    <svg
      class="sprite"
      [attr.viewBox]="viewBox()"
      [style.width.px]="pixelWidth()"
      shape-rendering="crispEdges"
      [attr.role]="label() ? 'img' : null"
      [attr.aria-label]="label() || null"
      [attr.aria-hidden]="label() ? null : 'true'"
    >
      @for (cell of cells(); track cell.id) {
        <rect [attr.x]="cell.x" [attr.y]="cell.y" width="1" height="1" />
      }
    </svg>
  `,
  styles: `
    :host {
      display: inline-block;
      line-height: 0;
    }
    .sprite {
      height: auto;
      fill: currentColor;
    }
  `,
})
export class PixelDino {
  readonly sprite = input<SpriteName>('trex');
  /** Size of one pixel cell, in screen px. */
  readonly scale = input(6);
  /** Set to give the sprite meaning for screen readers; omit for decoration. */
  readonly label = input('');
  /** Mirror horizontally, so a herd is not all facing the same way. */
  readonly flip = input(false);

  private readonly grid = computed(() => SPRITES[this.sprite()]);

  protected readonly viewBox = computed(() => {
    const grid = this.grid();
    return `0 0 ${grid[0].length} ${grid.length}`;
  });

  protected readonly pixelWidth = computed(() => this.grid()[0].length * this.scale());

  protected readonly cells = computed(() => {
    const grid = this.grid();
    const width = grid[0].length;
    const mirror = this.flip();
    const out: { id: string; x: number; y: number }[] = [];
    grid.forEach((row, y) => {
      [...row].forEach((char, x) => {
        if (char === '#') {
          const px = mirror ? width - 1 - x : x;
          out.push({ id: `${px}-${y}`, x: px, y });
        }
      });
    });
    return out;
  });
}
