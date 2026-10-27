import { Component } from '@angular/core';

import { PixelDino, SpriteName } from '../pixel-dino/pixel-dino';

interface ReelItem {
  /* Path under web/public/. Leave null to show a pixel placeholder instead. */
  image: string | null;
  /* Shown only when `image` is null. */
  sprite: SpriteName;
}

const img = (n: number): ReelItem => ({ image: `memes/meme-${String(n).padStart(2, '0')}.jpg`, sprite: 'egg' });

/* Images live in web/public/memes/. Alternated between the reels so each
   side gets a mix of photos and cartoons. Each reel needs at least 4 or a
   tall window shows the same image twice at once. */
const LEFT: ReelItem[] = [img(1), img(3), img(5), img(7), img(9)];
const RIGHT: ReelItem[] = [img(2), img(4), img(6), img(8)];

@Component({
  selector: 'side-reels',
  imports: [PixelDino],
  templateUrl: './side-reels.html',
  styleUrl: './side-reels.scss',
})
export class SideReels {
  /* Each list is rendered twice back to back; the animation moves the track
     by exactly one copy's height, so the loop has no visible seam. */
  protected readonly left = [...LEFT, ...LEFT];
  protected readonly right = [...RIGHT, ...RIGHT];
}
