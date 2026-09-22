import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/* Anything marked PLACEHOLDER is club info only Vlad can fill in. It is
   deliberately obvious rather than plausible-looking, so a wrong meeting time
   cannot quietly ship to a real page. */
@Component({
  selector: 'app-about',
  imports: [RouterLink],
  templateUrl: './about.html',
  styleUrl: './about.scss',
})
export class About {
  protected readonly meeting = {
    day: 'PLACEHOLDER — e.g. Thursdays',
    time: 'PLACEHOLDER — e.g. 7:30pm',
    place: 'PLACEHOLDER — building and room',
  };

  protected readonly contact = {
    email: 'PLACEHOLDER — club email',
    instagram: 'PLACEHOLDER — handle',
    discord: 'PLACEHOLDER — invite link',
  };

  protected readonly rules = [
    {
      title: 'Everything counts',
      body: 'If it has a dinosaur in it, it is eligible. Kaiju are a grey area we argue about constantly and have never resolved.',
    },
    {
      title: 'Bad films are the point',
      body: 'A beloved classic and a $400,000 creature feature get the same runtime and the same attention. Often the cheap one is the better night.',
    },
    {
      title: 'Nobody has to have seen anything',
      body: 'No prior knowledge required, of film or of the Cretaceous. Showing up is the whole entry requirement.',
    },
    {
      title: 'Paleoaccuracy debates are encouraged',
      body: 'Pausing the film to say the raptors are the wrong size is not rude here. It is participation.',
    },
  ];
}
