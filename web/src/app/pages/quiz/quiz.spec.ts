import { TestBed } from '@angular/core/testing';

import { loadEngine } from '../../quiz/data';
import { Quiz } from './quiz';

function el(fixture: ReturnType<typeof TestBed.createComponent<Quiz>>): HTMLElement {
  return fixture.nativeElement as HTMLElement;
}

async function click(fixture: ReturnType<typeof TestBed.createComponent<Quiz>>, selector: string) {
  const target = el(fixture).querySelector<HTMLElement>(selector);
  if (!target) throw new Error(`nothing matches ${selector}`);
  target.click();
  await fixture.whenStable();
}

describe('Quiz page, end to end', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [Quiz] }).compileComponents();
  });

  it('starts on the intro with a START button', async () => {
    const fixture = TestBed.createComponent(Quiz);
    await fixture.whenStable();
    expect(el(fixture).querySelector('h1')?.textContent).toContain('WHICH DINO');
    expect(el(fixture).querySelector('.btn')?.textContent?.trim()).toBe('START');
  });

  it('walks every question and lands on a dinosaur', async () => {
    const fixture = TestBed.createComponent(Quiz);
    await fixture.whenStable();
    await click(fixture, '.btn');

    const total = el(fixture).querySelectorAll('.progress__cell').length;
    expect(total).toBeGreaterThan(0);

    for (let i = 0; i < total; i++) {
      expect(el(fixture).querySelector('.counter')?.textContent).toContain(`Q ${i + 1} / ${total}`);
      await click(fixture, '.opt'); // first option every time
    }

    const page = el(fixture);
    expect(page.querySelector('.youare')?.textContent).toContain('YOU ARE');
    expect(page.querySelector('h1')?.textContent?.trim().length).toBeGreaterThan(0);
    expect(page.querySelector('.match')?.textContent).toMatch(/\d+% MATCH/);
    const engine = loadEngine();
    if (engine.keys.length === 2) {
      // Every dinosaur on the map, one highlighted, plus your dot.
      expect(page.querySelectorAll('.map__dino').length).toBe(engine.dinosaurs.length);
      expect(page.querySelectorAll('.map__dino--win').length).toBe(1);
      expect(page.querySelector('.map__you')).not.toBeNull();
    } else {
      // One bar per axis, each with a you-marker and a winner-marker.
      expect(page.querySelectorAll('.barrow').length).toBe(engine.keys.length);
      expect(page.querySelectorAll('.barrow__you').length).toBe(engine.keys.length);
      expect(page.querySelectorAll('.barrow__dino').length).toBe(engine.keys.length);
    }
    expect(page.querySelectorAll('.others li').length).toBe(Math.min(4, engine.dinosaurs.length - 1));
  });

  it('BACK on the first question returns to the intro, otherwise undoes one answer', async () => {
    const fixture = TestBed.createComponent(Quiz);
    await fixture.whenStable();
    await click(fixture, '.btn');
    await click(fixture, '.opt');
    expect(el(fixture).querySelector('.counter')?.textContent).toContain('Q 2');
    await click(fixture, '.back');
    expect(el(fixture).querySelector('.counter')?.textContent).toContain('Q 1');
    await click(fixture, '.back');
    expect(el(fixture).querySelector('.btn')?.textContent?.trim()).toBe('START');
  });

  it('answers with the number keys', async () => {
    const fixture = TestBed.createComponent(Quiz);
    await fixture.whenStable();
    await click(fixture, '.btn');
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '2' }));
    await fixture.whenStable();
    expect(el(fixture).querySelector('.counter')?.textContent).toContain('Q 2');
  });

  it('PLAY AGAIN resets to a fresh run', async () => {
    const fixture = TestBed.createComponent(Quiz);
    await fixture.whenStable();
    await click(fixture, '.btn');
    const total = el(fixture).querySelectorAll('.progress__cell').length;
    for (let i = 0; i < total; i++) await click(fixture, '.opt');
    await click(fixture, '.btn--alt');
    expect(el(fixture).querySelector('.counter')?.textContent).toContain('Q 1');
  });
});
