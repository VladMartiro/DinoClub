import { Component } from '@angular/core';

import { PixelDino, SpriteName } from '../pixel-dino/pixel-dino';

interface ReelItem {
  /* Not displayed -- kept so each tile stays identifiable when posters go in. */
  title: string;
  /* Path to a poster in web/public/, e.g. 'posters/jurassic-park.jpg'.
     Leave null and the tile renders a pixel placeholder instead. */
  image: string | null;
  sprite: SpriteName;
}

/* Placeholders for now. Left reel = films the club has watched, right reel =
   films on the list. Swap `image` in per tile when real posters exist. */
const WATCHED: ReelItem[] = [
  { title: 'JURASSIC PARK', image: null, sprite: 'trex' },
  { title: 'THE LAND BEFORE TIME', image: null, sprite: 'sauropod' },
  { title: 'GODZILLA', image: null, sprite: 'spino' },
  { title: 'KING KONG', image: null, sprite: 'raptor' },
  { title: 'DINOSAUR', image: null, sprite: 'trike' },
  { title: 'WALKING WITH DINOSAURS', image: null, sprite: 'para' },
];

const UP_NEXT: ReelItem[] = [
  { title: 'THE LOST WORLD', image: null, sprite: 'raptor' },
  { title: 'PREHISTORIC PLANET', image: null, sprite: 'ptera' },
  { title: 'THE GOOD DINOSAUR', image: null, sprite: 'galli' },
  { title: 'CARNOSAUR', image: null, sprite: 'dilo' },
  { title: 'VALLEY OF GWANGI', image: null, sprite: 'ankylo' },
  { title: '65', image: null, sprite: 'pachy' },
];

@Component({
  selector: 'side-reels',
  imports: [PixelDino],
  templateUrl: './side-reels.html',
  styleUrl: './side-reels.scss',
})
export class SideReels {
  /* Each list is rendered twice back to back; the animation moves the track
     by exactly one copy's height, so the loop has no visible seam. */
  protected readonly left = [...WATCHED, ...WATCHED];
  protected readonly right = [...UP_NEXT, ...UP_NEXT];
}
