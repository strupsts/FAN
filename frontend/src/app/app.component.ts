import { Component, inject } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';

import {
  LocalizationBootstrapService,
} from './core/i18n/localization-bootstrap.service';

@Component({
  selector: 'app-root',
  templateUrl: 'app.component.html',
  imports: [IonApp, IonRouterOutlet],
})
export class AppComponent {
  private readonly localizationBootstrap = inject(
    LocalizationBootstrapService,
  );

  constructor() {
    this.localizationBootstrap.initialize();
  }
}
