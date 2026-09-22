import { Component, signal } from '@angular/core';

import { PixelDino } from '../../shared/pixel-dino/pixel-dino';

/* Shell page. `findFilm()` will post taste answers to the Python recommender
   (dinoclub.recommend) once an API exists. */
@Component({
  selector: 'app-recommender',
  imports: [PixelDino],
  templateUrl: './recommender.html',
  styleUrl: './recommender.scss',
})
export class Recommender {
  protected readonly searching = signal(false);

  protected findFilm(): void {
    this.searching.set(true);
  }

  protected reset(): void {
    this.searching.set(false);
  }
}
