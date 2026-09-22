import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PixelDino } from '../../shared/pixel-dino/pixel-dino';

@Component({
  selector: 'app-home',
  imports: [RouterLink, PixelDino],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  /* PLACEHOLDER: swap in the real invite / club page URLs. */
  protected readonly discordUrl = 'https://discord.gg/PLACEHOLDER';
  protected readonly uncClubUrl = 'https://PLACEHOLDER';
}
