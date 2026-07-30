import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import {
  TranslocoService,
} from '@jsverse/transloco';

import {
  DEFAULT_LANGUAGE,
  INTERFACE_LANGUAGE_STORAGE_KEY,
  LocalizationService,
} from './localization.service';

describe('LocalizationService', () => {
  let service: LocalizationService;
  let document: Document;
  let transloco: jasmine.SpyObj<TranslocoService>;

  beforeEach(() => {
    transloco =
      jasmine.createSpyObj<TranslocoService>(
        'TranslocoService',
        [
          'setActiveLang',
        ],
      );

    TestBed.configureTestingModule({
      providers: [
        {
          provide: TranslocoService,
          useValue: transloco,
        },
      ],
    });

    service = TestBed.inject(LocalizationService);
    document = TestBed.inject(DOCUMENT);

    document.defaultView?.localStorage.removeItem(
      INTERFACE_LANGUAGE_STORAGE_KEY,
    );
  });

  afterEach(() => {
    document.defaultView?.localStorage.removeItem(
      INTERFACE_LANGUAGE_STORAGE_KEY,
    );

    document.documentElement.setAttribute(
      'lang',
      DEFAULT_LANGUAGE,
    );
    document.documentElement.setAttribute(
      'dir',
      'ltr',
    );
  });

  it('persists and applies a supported language', () => {
    const language = service.setLanguage('ru-RU');

    expect(language).toBe('ru');
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith('ru');
    expect(
      document.documentElement.getAttribute('lang'),
    ).toBe('ru');
    expect(
      document.documentElement.getAttribute('dir'),
    ).toBe('ltr');
    expect(
      document.defaultView?.localStorage.getItem(
        INTERFACE_LANGUAGE_STORAGE_KEY,
      ),
    ).toBe('ru');
  });

  it('restores the locally cached language', () => {
    document.defaultView?.localStorage.setItem(
      INTERFACE_LANGUAGE_STORAGE_KEY,
      'ru',
    );

    const language = service.initialize();

    expect(language).toBe('ru');
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith('ru');
  });

  it('falls back to English for an unsupported language', () => {
    const language = service.setLanguage('fr-CA');

    expect(language).toBe(DEFAULT_LANGUAGE);
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith(DEFAULT_LANGUAGE);
    expect(
      document.defaultView?.localStorage.getItem(
        INTERFACE_LANGUAGE_STORAGE_KEY,
      ),
    ).toBe(DEFAULT_LANGUAGE);
  });

  it('falls back to English for a missing language', () => {
    const language = service.setLanguage(undefined);

    expect(language).toBe(DEFAULT_LANGUAGE);
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith(DEFAULT_LANGUAGE);
  });

  it('falls back to English when cached language access fails', () => {
    const storage = document.defaultView?.localStorage;

    expect(storage).toBeDefined();
    spyOn(storage as Storage, 'getItem').and.throwError(
      'storage unavailable',
    );

    expect(() => service.initialize()).not.toThrow();
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith(DEFAULT_LANGUAGE);
  });

  it('applies a language when local persistence fails', () => {
    const storage = document.defaultView?.localStorage;

    expect(storage).toBeDefined();
    spyOn(storage as Storage, 'setItem').and.throwError(
      'storage unavailable',
    );

    expect(() => service.setLanguage('ru')).not.toThrow();
    expect(
      transloco.setActiveLang,
    ).toHaveBeenCalledOnceWith('ru');
    expect(
      document.documentElement.getAttribute('lang'),
    ).toBe('ru');
  });
});
