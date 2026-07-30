import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import type {
  components,
} from './generated/openapi-types';


export type CurrentUserProfileResponse =
  components['schemas']['CurrentUserProfileResponse'];

@Injectable({
  providedIn: 'root',
})
export class UserApiService {
  private readonly http = inject(HttpClient);

  getCurrentUser(): Observable<CurrentUserProfileResponse> {
    return this.http.get<CurrentUserProfileResponse>(
      `${environment.apiBaseUrl}/api/users/me`,
    );
  }
}
