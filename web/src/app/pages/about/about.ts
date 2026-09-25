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
    { name: 'Muskan Fatima', role: 'President', photo: null, sprite: 'trex' },
    { name: 'Vladimir Martirosyan', role: 'Vice-President', photo: null, sprite: 'raptor' },
    { name: 'Sarah Bernstein', role: 'Treasurer', photo: null, sprite: 'trike' },
    { name: 'Subin Seo', role: 'Officer', photo: null, sprite: 'para' },
  ];
}
