import { Component } from '@angular/core';

import { PixelDino, SpriteName } from '../../shared/pixel-dino/pixel-dino';

interface Member {
  name: string;
  role: string;
  /* Drop a square image in web/public/crew/ and put the path here, e.g.
     'crew/vlad.png'. Leave null and the slot renders a pixel placeholder. */
  photo: string | null;
  sprite: SpriteName;
}

@Component({
  selector: 'app-about',
  imports: [PixelDino],
  templateUrl: './about.html',
  styleUrl: './about.scss',
})
export class About {
  protected readonly crew: Member[] = [
    { name: 'PLAYER ONE', role: 'PLACEHOLDER', photo: null, sprite: 'trex' },
    { name: 'PLAYER TWO', role: 'PLACEHOLDER', photo: null, sprite: 'sauropod' },
    { name: 'PLAYER THREE', role: 'PLACEHOLDER', photo: null, sprite: 'trex' },
    { name: 'PLAYER FOUR', role: 'PLACEHOLDER', photo: null, sprite: 'egg' },
  ];
}
