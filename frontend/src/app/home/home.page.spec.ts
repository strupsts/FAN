import { HttpErrorResponse } from '@angular/common/http';
import {
  ComponentFixture,
  TestBed,
} from '@angular/core/testing';
import {
  Translation,
  TranslocoService,
  TranslocoTestingModule,
} from '@jsverse/transloco';
import { throwError } from 'rxjs';

import {
  ReceiptApiService,
} from '../core/api/receipt-api.service';
import {
  ConfirmedReceiptResponse,
  ReceiptItemResponse,
} from '../core/models/receipt.models';
import { HomePage } from './home.page';

async function loadTranslation(
  language: string,
): Promise<Translation> {
  const response = await fetch(
    `assets/i18n/${language}.json`,
  );

  if (!response.ok) {
    throw new Error(
      `Could not load ${language} translations.`,
    );
  }

  return response.json() as Promise<Translation>;
}

describe('HomePage', () => {
  let component: HomePage;
  let fixture: ComponentFixture<HomePage>;
  let receiptApi: jasmine.SpyObj<ReceiptApiService>;
  let transloco: TranslocoService;
  let english: Translation;
  let russian: Translation;

  beforeAll(async () => {
    [english, russian] = await Promise.all([
      loadTranslation('en'),
      loadTranslation('ru'),
    ]);
  });

  beforeEach(async () => {
    receiptApi = jasmine.createSpyObj<ReceiptApiService>(
      'ReceiptApiService',
      [
        'processReceipt',
        'confirmReceipt',
      ],
    );

    await TestBed.configureTestingModule({
      imports: [
        HomePage,
        TranslocoTestingModule.forRoot({
          langs: {
            en: english,
            ru: russian,
          },
          preloadLangs: true,
          translocoConfig: {
            availableLangs: ['en', 'ru'],
            defaultLang: 'en',
            fallbackLang: 'en',
            reRenderOnLangChange: true,
          },
        }),
      ],
      providers: [
        {
          provide: ReceiptApiService,
          useValue: receiptApi,
        },
      ],
    }).compileComponents();

    transloco = TestBed.inject(TranslocoService);
    transloco.setActiveLang('en');

    fixture = TestBed.createComponent(HomePage);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('renders Home-owned text in English', () => {
    expect(component).toBeTruthy();
    expect(textOf('ion-title')).toBe('F.A.N.');
    expect(textOf('.intro .eyebrow')).toBe(
      'Receipt assistant',
    );
    expect(textOf('h1')).toBe('Scan a receipt');
    expect(textOf('.intro-copy')).toContain(
      'Take a clear photo or choose one from your gallery.',
    );
    expect(textOf('.upload-panel strong')).toBe(
      'Take or choose a photo',
    );
  });

  it('updates existing rendered Home text in Russian', async () => {
    const originalComponent = component;

    await setLanguage('ru');

    expect(component).toBe(originalComponent);
    expect(textOf('.intro .eyebrow')).toBe(
      'Помощник по чекам',
    );
    expect(textOf('h1')).toBe('Отсканируйте чек');
    expect(textOf('.upload-panel strong')).toBe(
      'Сфотографировать или выбрать фото',
    );
  });

  it('translates preview text without changing the file name', async () => {
    component.selectedFile.set(
      new File(
        ['receipt'],
        'SHOPPERS-RECEIPT.JPG',
        {
          type: 'image/jpeg',
        },
      ),
    );
    component.previewUrl.set('blob:receipt-preview');

    await setLanguage('ru');

    const preview = element<HTMLImageElement>(
      '.receipt-preview',
    );

    expect(preview.alt).toBe(
      'Предпросмотр выбранного чека',
    );
    expect(textOf('.file-name')).toBe(
      'SHOPPERS-RECEIPT.JPG',
    );
    expect(textOf('.primary-action')).toContain(
      'Распознать чек',
    );
    expect(textOf('.button-stack ion-button:last-child'))
      .toContain('Выбрать другое фото');
  });

  it('localizes the unsupported-file message', () => {
    const input = document.createElement('input');
    const file = new File(['text'], 'receipt.txt', {
      type: 'text/plain',
    });

    Object.defineProperty(input, 'files', {
      value: [file],
    });

    component.onFileSelected({
      target: input,
    } as unknown as Event);
    fixture.detectChanges();

    expect(textOf('[role="alert"]')).toBe(
      'Choose a JPG, PNG, HEIC, or another image file.',
    );
  });

  it('maps known HTTP receipt errors to localized messages', async () => {
    const cases = [
      {
        status: 0,
        expected:
          'The backend is unavailable. Check that make dev is running.',
      },
      {
        status: 404,
        expected:
          'The original receipt draft could not be found.',
      },
      {
        status: 409,
        expected:
          'This receipt draft has already been confirmed.',
      },
      {
        status: 422,
        expected:
          'The receipt contains missing or invalid information.',
      },
      {
        status: 503,
        expected:
          'The receipt model is starting. Try again in a few seconds.',
      },
    ];

    for (const testCase of cases) {
      const message = await renderProcessError(
        new HttpErrorResponse({
          status: testCase.status,
        }),
      );

      expect(message)
        .withContext(`HTTP ${testCase.status}`)
        .toBe(testCase.expected);
    }
  });

  it('localizes non-HTTP and generic HTTP failures', async () => {
    expect(
      await renderProcessError(new Error('unexpected')),
    ).toBe('The receipt request failed.');

    expect(
      await renderProcessError(
        new HttpErrorResponse({
          status: 500,
        }),
      ),
    ).toBe('The receipt request failed.');
  });

  it('updates a displayed key-based error after a language change', async () => {
    await renderProcessError(
      new HttpErrorResponse({
        status: 0,
      }),
    );

    expect(textOf('[role="alert"]')).toContain(
      'The backend is unavailable.',
    );

    await setLanguage('ru');

    expect(textOf('[role="alert"]')).toBe(
      'Сервер недоступен. Убедитесь, что запущена команда make dev.',
    );
  });

  it('renders unknown backend detail as plain text', async () => {
    const detail =
      'home.errors.invalidReceipt <strong>diagnostic</strong>';

    await renderProcessError(
      new HttpErrorResponse({
        status: 500,
        error: {
          detail,
        },
      }),
    );

    expect(textOf('[role="alert"]')).toBe(detail);
    expect(
      element<HTMLElement>('[role="alert"]')
        .querySelector('strong'),
    ).toBeNull();

    await setLanguage('ru');

    expect(textOf('[role="alert"]')).toBe(detail);
  });

  it('uses English item plural forms for 1 and 2', () => {
    const cases = [
      {
        count: 1,
        expected: '1 purchase item was saved',
      },
      {
        count: 2,
        expected: '2 purchase items were saved',
      },
    ];

    for (const testCase of cases) {
      showConfirmedReceipt(testCase.count);

      expect(textOf('.success-copy'))
        .withContext(`English count ${testCase.count}`)
        .toContain(testCase.expected);
    }
  });

  it('uses Russian plural forms for 1, 2, 5, and 21', async () => {
    await setLanguage('ru');

    const cases = [
      {
        count: 1,
        expected: 'Сохранён 1 товар',
      },
      {
        count: 2,
        expected: 'Сохранено 2 товара',
      },
      {
        count: 5,
        expected: 'Сохранено 5 товаров',
      },
      {
        count: 21,
        expected: 'Сохранён 21 товар',
      },
    ];

    for (const testCase of cases) {
      showConfirmedReceipt(testCase.count);

      expect(textOf('.success-copy'))
        .withContext(`Russian count ${testCase.count}`)
        .toContain(testCase.expected);
    }
  });

  it('preserves merchant and money source text in Russian', async () => {
    await setLanguage('ru');
    showConfirmedReceipt(1, 'SHOPPERS DRUG MART');

    expect(textOf('.success-card h2')).toBe(
      'SHOPPERS DRUG MART',
    );
    expect(textOf('.success-total')).toBe('CAD 12.30');
    expect(textOf('.success-card .eyebrow')).toBe(
      'Чек сохранён',
    );
    expect(textOf('.success-card ion-button')).toContain(
      'Отсканировать ещё один чек',
    );
  });

  it('localizes the missing merchant fallback', async () => {
    await setLanguage('ru');
    showConfirmedReceipt(1, null);

    expect(textOf('.success-card h2')).toBe(
      'Чек подтверждён',
    );
  });

  async function setLanguage(language: string): Promise<void> {
    transloco.setActiveLang(language);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  async function renderProcessError(
    error: unknown,
  ): Promise<string> {
    component.selectedFile.set(
      new File(['receipt'], 'receipt.jpg', {
        type: 'image/jpeg',
      }),
    );
    receiptApi.processReceipt.and.returnValue(
      throwError(() => error),
    );

    await component.processReceipt();
    fixture.detectChanges();

    return textOf('[role="alert"]');
  }

  function showConfirmedReceipt(
    itemCount: number,
    merchantName: string | null = 'Source Merchant',
  ): void {
    component.confirmedReceipt.set(
      confirmedReceipt(itemCount, merchantName),
    );
    fixture.detectChanges();
  }

  function confirmedReceipt(
    itemCount: number,
    merchantName: string | null,
  ): ConfirmedReceiptResponse {
    const items: ReceiptItemResponse[] = Array.from(
      {
        length: itemCount,
      },
      (_, index) => ({
        name: `Source item ${index + 1}`,
        total_price: {
          amount: '12.30',
          currency: 'CAD',
        },
        category: 'groceries',
        bucket: 'needs',
        quantity: 1,
        unit_price: null,
        confidence: null,
      }),
    );

    return {
      id: 'receipt-1',
      user_id: 'user-1',
      merchant_name: merchantName,
      purchased_at: '2026-08-03T10:00:00',
      subtotal: null,
      tax: null,
      total: {
        amount: '12.30',
        currency: 'CAD',
      },
      image_ref: null,
      items,
    };
  }

  function element<T extends Element>(selector: string): T {
    const match = (
      fixture.nativeElement as HTMLElement
    ).querySelector<T>(selector);

    if (match === null) {
      throw new Error(`Missing test element: ${selector}`);
    }

    return match;
  }

  function textOf(selector: string): string {
    return element<HTMLElement>(selector)
      .textContent
      ?.replace(/\s+/g, ' ')
      .trim()
      ?? '';
  }
});
