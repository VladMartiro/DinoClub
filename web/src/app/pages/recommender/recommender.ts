import { Component, signal } from '@angular/core';

/* Shell page, same deal as the quiz: layout and button are real, engine is
   not attached. `findFilm()` will eventually post the user's taste answers to
   the Python recommender (dinoclub.recommend) and render the ranked films it
   returns, with the reason strings it already produces. */
@Component({
  selector: 'app-recommender',
  templateUrl: './recommender.html',
  styleUrl: './recommender.scss',
})
export class Recommender {
  protected readonly searching = signal(false);

  /* A slice of src/dinoclub/recommend/data/catalog.json, hardcoded so the
     shell renders standalone. Replaced by the API response later. */
  protected readonly sampleAxes = [
    'spectacle',
    'dread',
    'camp',
    'wonder',
    'heart',
    'science',
    'retro',
    'kaiju',
    'kid',
    'grit',
  ];

  protected readonly notes = [
    {
      title: 'Built for a small library',
      body: 'Twenty-eight films, not twenty-eight thousand. Most recommender tutorials assume a dataset we do not have.',
    },
    {
      title: 'Works with zero ratings',
      body: 'Every film is placed by hand on ten taste axes, so the first person to use it gets a real answer rather than a shrug.',
    },
    {
      title: 'Picks its own questions',
      body: 'It asks whichever question tells it the most about you next, so six questions do the work of twenty.',
    },
    {
      title: 'Will not give you five sequels',
      body: 'The list gets re-ranked for variety, because pure relevance on a catalogue this size returns the same franchise every time.',
    },
  ];

  protected findFilm(): void {
    this.searching.set(true);
  }

  protected reset(): void {
    this.searching.set(false);
  }
}
