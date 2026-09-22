import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  imports: [RouterLink],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  protected readonly features = [
    {
      tag: 'Quiz',
      title: 'What type of dinosaur are you?',
      body: 'Ten questions, four behavioral axes, one dinosaur. It scores you on traits and matches you to the closest archetype rather than counting points per dinosaur.',
      link: '/quiz',
      cta: 'Take the test',
    },
    {
      tag: 'Recommender',
      title: 'Find your next film',
      body: 'Tell us what you like and we pick from the club catalogue. Built to handle a small library and cold starts, so it works before anyone has rated anything.',
      link: '/recommender',
      cta: 'Get a recommendation',
    },
  ];

  protected readonly stats = [
    { value: '10', label: 'dinosaur archetypes' },
    { value: '4', label: 'trait axes' },
    { value: '28', label: 'films in the catalogue' },
  ];
}
