import { inject, Injectable } from '@angular/core';
import {
  catchError,
  EMPTY,
  take,
} from 'rxjs';

import {
  UserApiService,
} from '../api/user-api.service';
import {
  LocalizationService,
} from './localization.service';

@Injectable({
  providedIn: 'root',
})
export class LocalizationBootstrapService {
  private readonly localization = inject(
    LocalizationService,
  );
  private readonly userApi = inject(UserApiService);

  initialize(): void {
    this.localization.initialize();

    this.userApi
      .getCurrentUser()
      .pipe(
        take(1),
        catchError(() => EMPTY),
      )
      .subscribe((profile) => {
        this.localization.setLanguage(
          profile.preferences?.interface_language,
        );
      });
  }
}
