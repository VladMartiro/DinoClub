import { TestBed } from '@angular/core/testing';

import { PixelDino } from './pixel-dino';

describe('PixelDino', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [PixelDino] }).compileComponents();
  });

  it('renders one rect per filled pixel', async () => {
    const fixture = TestBed.createComponent(PixelDino);
    fixture.componentRef.setInput('sprite', 'egg');
    await fixture.whenStable();

    const rects = (fixture.nativeElement as HTMLElement).querySelectorAll('rect');
    // The egg sprite is solid, so it should be a lot of pixels but not the
    // whole 16x16 grid -- if it were, the sprite data got flattened somewhere.
    expect(rects.length).toBeGreaterThan(100);
    expect(rects.length).toBeLessThan(16 * 16);
  });

  it('keeps crisp edges so the art does not blur when scaled', async () => {
    const fixture = TestBed.createComponent(PixelDino);
    await fixture.whenStable();
    const svg = (fixture.nativeElement as HTMLElement).querySelector('svg');
    expect(svg?.getAttribute('shape-rendering')).toBe('crispEdges');
  });

  it('sizes the viewBox to the sprite grid', async () => {
    const fixture = TestBed.createComponent(PixelDino);
    await fixture.whenStable();
    const svg = (fixture.nativeElement as HTMLElement).querySelector('svg');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 16 16');
  });

  it('mirrors horizontally when flipped', async () => {
    const plain = TestBed.createComponent(PixelDino);
    await plain.whenStable();
    const flipped = TestBed.createComponent(PixelDino);
    flipped.componentRef.setInput('flip', true);
    await flipped.whenStable();

    const xs = (fixture: typeof plain) =>
      Array.from(
        (fixture.nativeElement as HTMLElement).querySelectorAll('rect'),
      ).map((r) => r.getAttribute('x'));

    expect(xs(flipped)).not.toEqual(xs(plain));
    expect(xs(flipped).length).toBe(xs(plain).length);
  });

  it('is hidden from screen readers unless given a label', async () => {
    const decorative = TestBed.createComponent(PixelDino);
    await decorative.whenStable();
    expect(
      (decorative.nativeElement as HTMLElement)
        .querySelector('svg')
        ?.getAttribute('aria-hidden'),
    ).toBe('true');

    const meaningful = TestBed.createComponent(PixelDino);
    meaningful.componentRef.setInput('label', 'A tyrannosaurus');
    await meaningful.whenStable();
    const svg = (meaningful.nativeElement as HTMLElement).querySelector('svg');
    expect(svg?.getAttribute('aria-hidden')).toBeNull();
    expect(svg?.getAttribute('role')).toBe('img');
  });
});
