import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';
import { routes } from './app.routes';

describe('App shell', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes)],
    }).compileComponents();
  });

  it('creates the app', () => {
    expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
  });

  it('renders every nav link', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    const labels = Array.from(el.querySelectorAll('.nav a')).map((a) =>
      a.textContent?.trim(),
    );
    expect(labels).toEqual(['HOME', 'QUIZ', 'FILMS', 'CREW']);
  });

  it('has a route for every nav link', () => {
    const paths = routes.map((route) => route.path);
    for (const link of ['', 'quiz', 'recommender', 'about']) {
      expect(paths).toContain(link);
    }
  });
});
