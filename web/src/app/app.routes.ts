import { Routes } from '@angular/router';

/* Pages are lazy-loaded so the landing page ships on its own, and so the
   quiz and recommender bundles stay separate once they carry real logic. */
export const routes: Routes = [
  {
    path: '',
    title: 'Dino Club',
    loadComponent: () => import('./pages/home/home').then((m) => m.Home),
  },
  {
    path: 'quiz',
    title: 'Personality Test | Dino Club',
    loadComponent: () => import('./pages/quiz/quiz').then((m) => m.Quiz),
  },
  {
    path: 'recommender',
    title: 'Film Recommender | Dino Club',
    loadComponent: () =>
      import('./pages/recommender/recommender').then((m) => m.Recommender),
  },
  {
    path: 'about',
    title: 'About Us | Dino Club',
    loadComponent: () => import('./pages/about/about').then((m) => m.About),
  },
  { path: '**', redirectTo: '' },
];
