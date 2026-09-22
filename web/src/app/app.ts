import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { PixelDino } from './shared/pixel-dino/pixel-dino';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, PixelDino],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly navOpen = signal(false);

  protected readonly links = [
    { path: '/', label: 'HOME', exact: true },
    { path: '/quiz', label: 'QUIZ', exact: false },
    { path: '/recommender', label: 'FILMS', exact: false },
    { path: '/about', label: 'CREW', exact: false },
  ];

  protected toggleNav(): void {
    this.navOpen.update((open) => !open);
  }

  protected closeNav(): void {
    this.navOpen.set(false);
  }
}
