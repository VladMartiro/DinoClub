import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

type Theme = 'dark' | 'light';

const THEME_KEY = 'dinoclub.theme';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly navOpen = signal(false);
  protected readonly theme = signal<Theme>(this.readStoredTheme());

  protected readonly links = [
    { path: '/', label: 'Home', exact: true },
    { path: '/quiz', label: 'Personality Test', exact: false },
    { path: '/recommender', label: 'Recommender', exact: false },
    { path: '/about', label: 'About Us', exact: false },
  ];

  constructor() {
    this.applyTheme(this.theme());
  }

  protected toggleNav(): void {
    this.navOpen.update((open) => !open);
  }

  protected closeNav(): void {
    this.navOpen.set(false);
  }

  protected toggleTheme(): void {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    this.applyTheme(next);
    // Storage can throw in private browsing, and a failed preference save is
    // never worth breaking the page over.
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* ignore */
    }
  }

  private applyTheme(theme: Theme): void {
    document.documentElement.setAttribute('data-theme', theme);
  }

  private readStoredTheme(): Theme {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored === 'dark' || stored === 'light') {
        return stored;
      }
    } catch {
      /* ignore */
    }
    return 'dark';
  }
}
