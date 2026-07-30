import {
  provideHttpClient,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  CurrentUserProfileResponse,
  UserApiService,
} from './user-api.service';

describe('UserApiService', () => {
  let service: UserApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(UserApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('gets the current user profile', () => {
    const profile: CurrentUserProfileResponse = {
      id: '00000000-0000-4000-8000-000000000001',
      created_at: '2026-07-30T01:00:00Z',
      preferences: null,
    };

    service.getCurrentUser().subscribe((result) => {
      expect(result).toEqual(profile);
    });

    const request = http.expectOne('/api/users/me');

    expect(request.request.method).toBe('GET');

    request.flush(profile);
  });
});
