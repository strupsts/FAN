import { DOCUMENT } from '@angular/common';
import { inject, Injectable } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';


export const SUPPORTED_LANGUAGES = [
  'en',
  'ru',
] as const;

export type SupportedLanguage =
  (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'en';

const RTL_LANGUAGE_CODES = new Set([
  'ar',
  'fa',
  'he',
  'ur',
]);


@Injectable({
  providedIn: 'root',
})
export class LocalizationService {
  private readonly document = inject(DOCUMENT);
  private readonly transloco = inject(TranslocoService);

  initialize(
    language: string | null | undefined = DEFAULT_LANGUAGE,
  ): SupportedLanguage {
    return this.setLanguage(language);
  }

  setLanguage(
    language: string | null | undefined,
  ): SupportedLanguage {
    const normalizedLanguage = (
      language
        ?.trim()
        .toLowerCase()
        .split(/[-_]/)[0]
      ?? ''
    );

    const activeLanguage = this.isSupportedLanguage(
      normalizedLanguage,
    )
      ? normalizedLanguage
      : DEFAULT_LANGUAGE;

    this.transloco.setActiveLang(activeLanguage);

    this.document.documentElement.setAttribute(
      'lang',
      activeLanguage,
    );
    this.document.documentElement.setAttribute(
      'dir',
      RTL_LANGUAGE_CODES.has(activeLanguage)
        ? 'rtl'
        : 'ltr',
    );

    return activeLanguage;
  }

  private isSupportedLanguage(
    language: string,
  ): language is SupportedLanguage {
    return (
      SUPPORTED_LANGUAGES as readonly string[]
    ).includes(language);
  }
}
