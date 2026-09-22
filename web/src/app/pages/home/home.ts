import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PixelDino } from '../../shared/pixel-dino/pixel-dino';

@Component({
  selector: 'app-home',
  imports: [RouterLink, PixelDino],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  /* Shell buttons: no links yet. When the Discord invite and UNC club page
     exist, turn these back into <a [href]> and drop `pending`. */
  protected readonly pending = signal<string | null>(null);

  protected soon(what: string): void {
    this.pending.set(what);
  }
}
