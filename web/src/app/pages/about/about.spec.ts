import { TestBed } from '@angular/core/testing';

import { About } from './about';

describe('About page', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [About] }).compileComponents();
  });

  it('shows exactly four crew members for the 2x2 grid', async () => {
    const fixture = TestBed.createComponent(About);
    await fixture.whenStable();
    const cards = (fixture.nativeElement as HTMLElement).querySelectorAll('.card');
    expect(cards.length).toBe(4);
  });

  it('renders a photo placeholder wherever no image is set', async () => {
    const fixture = TestBed.createComponent(About);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.slot').length).toBe(4);
    expect(el.querySelectorAll('.shot img').length).toBe(0);
  });
});
