import { Component, inject } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';

import {
  LocalizationService,
} from './core/i18n/localization.service';

@Component({
  selector: 'app-root',
  templateUrl: 'app.component.html',
  imports: [IonApp, IonRouterOutlet],
})
export class AppComponent {
  private readonly localization = inject(
    LocalizationService,
  );

  constructor() {
    this.localization.initialize();
  }
}
