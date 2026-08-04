import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonContent,
  IonHeader,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import {
  TranslocoPipe,
  TranslocoService,
} from '@jsverse/transloco';
import { firstValueFrom } from 'rxjs';

import { ReceiptApiService } from '../core/api/receipt-api.service';
import {
  ConfirmedReceiptResponse,
  ConfirmReceiptRequest,
  MoneyResponse,
  ReceiptDraftResponse,
} from '../core/models/receipt.models';
import {
  ReceiptReviewFormComponent,
} from '../features/receipt-review/receipt-review-form.component';

const HOME_ERROR_KEYS = {
  unsupportedFile: 'home.errors.unsupportedFile',
  requestFailed: 'home.errors.requestFailed',
  backendUnavailable: 'home.errors.backendUnavailable',
  draftNotFound: 'home.errors.draftNotFound',
  alreadyConfirmed: 'home.errors.alreadyConfirmed',
  invalidReceipt: 'home.errors.invalidReceipt',
  modelStarting: 'home.errors.modelStarting',
  httpFallback: 'home.errors.httpFallback',
} as const;

type HomeErrorKey =
  (typeof HOME_ERROR_KEYS)[keyof typeof HOME_ERROR_KEYS];

type HomeError =
  | {
    kind: 'translation';
    key: HomeErrorKey;
  }
  | {
    kind: 'detail';
    detail: string;
  };

type ItemPluralTranslationKey =
  | 'home.success.savedItems.one'
  | 'home.success.savedItems.few'
  | 'home.success.savedItems.many'
  | 'home.success.savedItems.other';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  imports: [
    ReceiptReviewFormComponent,
    IonButton,
    IonCard,
    IonCardContent,
    IonContent,
    IonHeader,
    IonSpinner,
    IonTitle,
    IonToolbar,
    TranslocoPipe,
  ],
})
export class HomePage implements OnDestroy {
  private readonly receiptApi = inject(ReceiptApiService);
  private readonly transloco = inject(TranslocoService);
  private readonly activeLanguage = toSignal(
    this.transloco.langChanges$,
    {
      initialValue: this.transloco.getActiveLang(),
    },
  );

  readonly selectedFile = signal<File | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly draft = signal<ReceiptDraftResponse | null>(null);
  readonly confirmedReceipt =
    signal<ConfirmedReceiptResponse | null>(null);

  readonly isProcessing = signal(false);
  readonly isConfirming = signal(false);
  readonly error = signal<HomeError | null>(null);

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    if (file === null) {
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.error.set(
        this.translationError(
          HOME_ERROR_KEYS.unsupportedFile,
        ),
      );
      input.value = '';
      return;
    }

    this.revokePreview();

    this.selectedFile.set(file);
    this.previewUrl.set(URL.createObjectURL(file));
    this.draft.set(null);
    this.confirmedReceipt.set(null);
    this.error.set(null);
  }

  async processReceipt(): Promise<void> {
    const file = this.selectedFile();

    if (file === null || this.isProcessing()) {
      return;
    }

    this.isProcessing.set(true);
    this.error.set(null);
    this.draft.set(null);
    this.confirmedReceipt.set(null);

    try {
      const draft = await firstValueFrom(
        this.receiptApi.processReceipt(file),
      );

      this.draft.set(draft);
    } catch (error: unknown) {
      this.error.set(this.describeError(error));
    } finally {
      this.isProcessing.set(false);
    }
  }

  async confirmReceipt(
    request: ConfirmReceiptRequest,
  ): Promise<void> {
    if (this.isConfirming()) {
      return;
    }

    this.isConfirming.set(true);
    this.error.set(null);

    try {
      const receipt = await firstValueFrom(
        this.receiptApi.confirmReceipt(request),
      );

      this.confirmedReceipt.set(receipt);
      this.draft.set(null);
    } catch (error: unknown) {
      this.error.set(this.describeError(error));
    } finally {
      this.isConfirming.set(false);
    }
  }

  chooseAnother(input: HTMLInputElement): void {
    this.resetReceipt();
    input.value = '';
    input.click();
  }

  formatMoney(money: MoneyResponse): string {
    return `${money.currency} ${money.amount}`;
  }

  itemCountTranslationKey(
    count: number,
  ): ItemPluralTranslationKey {
    const category = new Intl.PluralRules(
      this.activeLanguage(),
    ).select(count);

    switch (category) {
      case 'one':
        return 'home.success.savedItems.one';
      case 'few':
        return 'home.success.savedItems.few';
      case 'many':
        return 'home.success.savedItems.many';
      default:
        return 'home.success.savedItems.other';
    }
  }

  ngOnDestroy(): void {
    this.revokePreview();
  }

  private resetReceipt(): void {
    this.revokePreview();

    this.selectedFile.set(null);
    this.previewUrl.set(null);
    this.draft.set(null);
    this.confirmedReceipt.set(null);
    this.error.set(null);
    this.isProcessing.set(false);
    this.isConfirming.set(false);
  }

  private revokePreview(): void {
    const currentUrl = this.previewUrl();

    if (currentUrl !== null) {
      URL.revokeObjectURL(currentUrl);
    }
  }

  private describeError(error: unknown): HomeError {
    if (!(error instanceof HttpErrorResponse)) {
      return this.translationError(
        HOME_ERROR_KEYS.requestFailed,
      );
    }

    if (error.status === 0) {
      return this.translationError(
        HOME_ERROR_KEYS.backendUnavailable,
      );
    }

    if (error.status === 404) {
      return this.translationError(
        HOME_ERROR_KEYS.draftNotFound,
      );
    }

    if (error.status === 409) {
      return this.translationError(
        HOME_ERROR_KEYS.alreadyConfirmed,
      );
    }

    if (error.status === 422) {
      return this.translationError(
        HOME_ERROR_KEYS.invalidReceipt,
      );
    }

    if (error.status === 503) {
      return this.translationError(
        HOME_ERROR_KEYS.modelStarting,
      );
    }

    const detail: unknown = error.error?.detail;

    if (
      typeof detail === 'string' &&
      detail.trim().length > 0
    ) {
      return {
        kind: 'detail',
        detail,
      };
    }

    return this.translationError(
      HOME_ERROR_KEYS.httpFallback,
    );
  }

  private translationError(key: HomeErrorKey): HomeError {
    return {
      kind: 'translation',
      key,
    };
  }
}
