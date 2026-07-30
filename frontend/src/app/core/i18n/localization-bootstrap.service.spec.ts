import { TestBed } from '@angular/core/testing';
import {
  of,
  Subject,
  throwError,
} from 'rxjs';

import {
  CurrentUserProfileResponse,
  UserApiService,
} from '../api/user-api.service';
import {
  LocalizationBootstrapService,
} from './localization-bootstrap.service';
import {
  LocalizationService,
} from './localization.service';

describe('LocalizationBootstrapService', () => {
  let bootstrap: LocalizationBootstrapService;
  let localization: jasmine.SpyObj<LocalizationService>;
  let userApi: jasmine.SpyObj<UserApiService>;

  beforeEach(() => {
    localization =
      jasmine.createSpyObj<LocalizationService>(
        'LocalizationService',
        [
          'initialize',
          'setLanguage',
        ],
      );

    userApi = jasmine.createSpyObj<UserApiService>(
      'UserApiService',
      [
        'getCurrentUser',
      ],
    );

    TestBed.configureTestingModule({
      providers: [
        {
          provide: LocalizationService,
          useValue: localization,
        },
        {
          provide: UserApiService,
          useValue: userApi,
        },
      ],
    });

    bootstrap = TestBed.inject(
      LocalizationBootstrapService,
    );
  });

  it('applies the server language after local startup', () => {
    const profile: CurrentUserProfileResponse = {
      id: '00000000-0000-4000-8000-000000000001',
      created_at: '2026-07-30T01:00:00Z',
      preferences: {
        user_id:
          '00000000-0000-4000-8000-000000000001',
        interface_language: 'ru',
        formatting_locale: 'en-CA',
        home_country: 'CA',
        default_receipt_currency: 'CAD',
        reporting_currency: 'CAD',
        time_zone: 'America/Edmonton',
        onboarding_completed: true,
        updated_at: '2026-07-30T01:00:00Z',
      },
    };

    userApi.getCurrentUser.and.returnValue(
      of(profile),
    );

    bootstrap.initialize();

    expect(
      localization.initialize,
    ).toHaveBeenCalledTimes(1);
    expect(
      localization.initialize,
    ).toHaveBeenCalledBefore(userApi.getCurrentUser);
    expect(
      localization.setLanguage,
    ).toHaveBeenCalledOnceWith('ru');
  });

  it('keeps the local language when the API is offline', () => {
    userApi.getCurrentUser.and.returnValue(
      throwError(() => new Error('offline')),
    );

    bootstrap.initialize();

    expect(
      localization.initialize,
    ).toHaveBeenCalledTimes(1);
    expect(
      localization.setLanguage,
    ).not.toHaveBeenCalled();
  });

  it('falls back to English when server preferences are missing', () => {
    const profile: CurrentUserProfileResponse = {
      id: '00000000-0000-4000-8000-000000000001',
      created_at: '2026-07-30T01:00:00Z',
      preferences: null,
    };

    userApi.getCurrentUser.and.returnValue(
      of(profile),
    );

    bootstrap.initialize();

    expect(
      localization.setLanguage,
    ).toHaveBeenCalledOnceWith(undefined);
  });

  it('completes the profile subscription after one response', () => {
    const profiles =
      new Subject<CurrentUserProfileResponse>();
    const profile: CurrentUserProfileResponse = {
      id: '00000000-0000-4000-8000-000000000001',
      created_at: '2026-07-30T01:00:00Z',
      preferences: null,
    };

    userApi.getCurrentUser.and.returnValue(profiles);

    bootstrap.initialize();

    expect(profiles.observed).toBeTrue();

    profiles.next(profile);

    expect(profiles.observed).toBeFalse();
    expect(
      localization.setLanguage,
    ).toHaveBeenCalledOnceWith(undefined);
  });
});
