import { Component, signal } from '@angular/core';

import { PixelDino } from '../../shared/pixel-dino/pixel-dino';

/* Shell page. Button is real, engine is not attached yet -- `start()` will
   call the Python scoring pipeline (dinoclub.quiz) once an API exists. */
@Component({
  selector: 'app-quiz',
  imports: [PixelDino],
  templateUrl: './quiz.html',
  styleUrl: './quiz.scss',
})
export class Quiz {
  protected readonly started = signal(false);

  protected readonly axes = [
    { low: 'FORAGER', high: 'HUNTER' },
    { low: 'PACK', high: 'SOLITARY' },
    { low: 'ARMOR', high: 'SPEED' },
    { low: 'BRUTE', high: 'CUNNING' },
  ];

  protected start(): void {
    this.started.set(true);
  }

  protected reset(): void {
    this.started.set(false);
  }
}
