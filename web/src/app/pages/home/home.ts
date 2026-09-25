import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CLUB } from '../../club';

@Component({
  selector: 'app-home',
  imports: [RouterLink],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  protected readonly discordUrl = CLUB.discordUrl;
  protected readonly uncClubUrl = CLUB.uncClubUrl;
}
