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

export const INTERFACE_LANGUAGE_STORAGE_KEY =
  'fan.interface_language';

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
    language?: string | null,
  ): SupportedLanguage {
    const initialLanguage =
      language
      ?? this.readStoredLanguage()
      ?? DEFAULT_LANGUAGE;

    return this.setLanguage(initialLanguage);
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

    this.persistLanguage(activeLanguage);

    return activeLanguage;
  }

  private readStoredLanguage(): string | null {
    try {
      return (
        this.document.defaultView?.localStorage.getItem(
          INTERFACE_LANGUAGE_STORAGE_KEY,
        )
        ?? null
      );
    } catch {
      return null;
    }
  }

  private persistLanguage(
    language: SupportedLanguage,
  ): void {
    try {
      this.document.defaultView?.localStorage.setItem(
        INTERFACE_LANGUAGE_STORAGE_KEY,
        language,
      );
    } catch {
      return;
    }
  }

  private isSupportedLanguage(
    language: string,
  ): language is SupportedLanguage {
    return (
      SUPPORTED_LANGUAGES as readonly string[]
    ).includes(language);
  }
}
