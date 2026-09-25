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
  protected readonly discordUrl = 'https://discord.gg/c7HWD5gHsS';
  protected readonly uncClubUrl = 'https://heellife.unc.edu/';
}
