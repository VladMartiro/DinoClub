import { Component, signal } from '@angular/core';

/* Shell page. The button and layout are real; the engine behind it is not
   wired up yet. When it is, `start()` will call into the Python scoring
   pipeline (dinoclub.quiz) via an API and hand back a Result payload --
   winner, match percentage, leaderboard and radar rows. */
@Component({
  selector: 'app-quiz',
  templateUrl: './quiz.html',
  styleUrl: './quiz.scss',
})
export class Quiz {
  protected readonly started = signal(false);

  /* Mirrors src/dinoclub/quiz/data/traits.json. Duplicated here on purpose
     for now: the shell should render without a backend. Once the API exists
     this comes from it, so the two cannot drift. */
  protected readonly axes = [
    { key: 'diet', negative: 'Herbivore / Forager', positive: 'Carnivore / Active Hunter' },
    { key: 'social', negative: 'Herd / Pack Player', positive: 'Solitary Apex' },
    { key: 'strategy', negative: 'Heavy Armor / Defense', positive: 'High Speed / Agility' },
    { key: 'temperament', negative: 'Brute Force / Instinct', positive: 'Calculating / Cunning' },
  ];

  protected readonly steps = [
    'Answer ten questions about how you actually behave, not about dinosaurs.',
    'Each answer shifts you along the four trait axes above.',
    'Your totals get calibrated onto the same scale the dinosaurs use.',
    'Closest dinosaur in 4D space wins, with a match percentage and runners-up.',
  ];

  protected start(): void {
    this.started.set(true);
  }

  protected reset(): void {
    this.started.set(false);
  }
}
