import { DecimalPipe, UpperCasePipe } from '@angular/common';
import { Component, HostListener, computed, signal } from '@angular/core';

import { loadEngine } from '../../quiz/data';
import { Answer, Match, Result } from '../../quiz/engine';
import { PixelDino, SpriteName } from '../../shared/pixel-dino/pixel-dino';

type Phase = 'intro' | 'asking' | 'result';

/* Which sprite draws which dinosaur. Anything not listed falls back to the
   egg, so adding a dinosaur to the data never breaks the page. */
const SPRITES: Record<string, SpriteName> = {
  tyrannosaurus: 'trex',
  velociraptor: 'raptor',
  ankylosaurus: 'ankylo',
  gallimimus: 'galli',
};

@Component({
  selector: 'app-quiz',
  imports: [PixelDino, UpperCasePipe, DecimalPipe],
  templateUrl: './quiz.html',
  styleUrl: './quiz.scss',
})
export class Quiz {
  protected readonly engine = loadEngine();

  protected readonly phase = signal<Phase>('intro');
  protected readonly index = signal(0);
  protected readonly answers = signal<Answer[]>([]);
  protected readonly result = signal<Result | null>(null);

  protected readonly questions = this.engine.questions;
  protected readonly total = this.questions.length;
  protected readonly current = computed(() => this.questions[this.index()]);

  /* The two axes, for the map. The mini dataset is two-dimensional by
     design; x is the first trait, y the second. */
  protected readonly xTrait = this.engine.space.traits[0];
  protected readonly yTrait = this.engine.space.traits[1];

  protected start(): void {
    this.answers.set([]);
    this.index.set(0);
    this.result.set(null);
    this.phase.set('asking');
  }

  protected answer(optionId: string): void {
    const q = this.current();
    this.answers.update((a) => [...a, [q.id, optionId]]);
    if (this.index() + 1 >= this.total) {
      this.result.set(this.engine.score(this.answers()));
      this.phase.set('result');
    } else {
      this.index.update((i) => i + 1);
    }
  }

  protected back(): void {
    if (this.index() === 0) {
      this.phase.set('intro');
      return;
    }
    this.answers.update((a) => a.slice(0, -1));
    this.index.update((i) => i - 1);
  }

  /* Arcade cabinets have number keys. */
  @HostListener('window:keydown', ['$event'])
  protected onKey(event: KeyboardEvent): void {
    if (this.phase() !== 'asking') return;
    const n = Number(event.key);
    const options = this.current().options;
    if (n >= 1 && n <= options.length) {
      event.preventDefault();
      this.answer(options[n - 1].id);
    }
  }

  protected sprite(dinosaurId: string): SpriteName {
    return SPRITES[dinosaurId] ?? 'egg';
  }

  /* Map a coordinate into 0..100% of the map's width or height. y is
     flipped so the positive pole sits at the top. */
  protected pct(value: number, flip = false): number {
    const t = (value - this.engine.min) / (this.engine.max - this.engine.min);
    return (flip ? 1 - t : t) * 100;
  }

  protected others(result: Result): Match[] {
    return result.matches.slice(1);
  }
}
