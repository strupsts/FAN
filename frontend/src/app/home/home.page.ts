import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonList,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { firstValueFrom } from 'rxjs';

import { ReceiptApiService } from '../core/api/receipt-api.service';
import {
  ConfirmedReceiptResponse,
  ConfirmReceiptRequest,
  MoneyResponse,
  ReceiptDraftResponse,
} from '../core/models/receipt.models';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  imports: [
    IonButton,
    IonCard,
    IonCardContent,
    IonContent,
    IonHeader,
    IonItem,
    IonLabel,
    IonList,
    IonSpinner,
    IonTitle,
    IonToolbar,
  ],
})
export class HomePage implements OnDestroy {
  private readonly receiptApi = inject(ReceiptApiService);

  readonly selectedFile = signal<File | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly draft = signal<ReceiptDraftResponse | null>(null);
  readonly confirmedReceipt =
    signal<ConfirmedReceiptResponse | null>(null);

  readonly isProcessing = signal(false);
  readonly isConfirming = signal(false);
  readonly errorMessage = signal<string | null>(null);

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    if (file === null) {
      return;
    }

    if (!file.type.startsWith('image/')) {
      this.errorMessage.set(
        'Choose a JPG, PNG, HEIC, or another image file.',
      );
      input.value = '';
      return;
    }

    this.revokePreview();

    this.selectedFile.set(file);
    this.previewUrl.set(URL.createObjectURL(file));
    this.draft.set(null);
    this.confirmedReceipt.set(null);
    this.errorMessage.set(null);
  }

  async processReceipt(): Promise<void> {
    const file = this.selectedFile();

    if (file === null || this.isProcessing()) {
      return;
    }

    this.isProcessing.set(true);
    this.errorMessage.set(null);
    this.draft.set(null);
    this.confirmedReceipt.set(null);

    try {
      const draft = await firstValueFrom(
        this.receiptApi.processReceipt(file),
      );

      this.draft.set(draft);
    } catch (error: unknown) {
      this.errorMessage.set(this.describeError(error));
    } finally {
      this.isProcessing.set(false);
    }
  }

  async confirmReceipt(): Promise<void> {
    const draft = this.draft();

    if (draft === null || this.isConfirming()) {
      return;
    }

    const request = this.buildConfirmRequest(draft);

    if (request === null) {
      this.errorMessage.set(
        'The receipt total was not detected. Editing will be added next.',
      );
      return;
    }

    this.isConfirming.set(true);
    this.errorMessage.set(null);

    try {
      const receipt = await firstValueFrom(
        this.receiptApi.confirmReceipt(request),
      );

      this.confirmedReceipt.set(receipt);
      this.draft.set(null);
    } catch (error: unknown) {
      this.errorMessage.set(this.describeError(error));
    } finally {
      this.isConfirming.set(false);
    }
  }

  chooseAnother(input: HTMLInputElement): void {
    this.resetReceipt();
    input.value = '';
    input.click();
  }

  formatMoney(money: MoneyResponse | null): string {
    if (money === null) {
      return 'Not detected';
    }

    return `${money.currency} ${money.amount}`;
  }

  formatDate(value: string | null): string {
    if (value === null) {
      return 'Date not detected';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }

  ngOnDestroy(): void {
    this.revokePreview();
  }

  private buildConfirmRequest(
    draft: ReceiptDraftResponse,
  ): ConfirmReceiptRequest | null {
    if (draft.total === null || draft.items.length === 0) {
      return null;
    }

    const defaultCurrency = draft.total.currency;

    return {
      draft_id: draft.id,
      merchant_name: draft.merchant_name,
      purchased_at: draft.purchased_at,
      image_ref: draft.image_ref,

      subtotal_amount: draft.subtotal?.amount ?? null,
      subtotal_currency:
        draft.subtotal?.currency ?? defaultCurrency,

      tax_amount: draft.tax?.amount ?? null,
      tax_currency: draft.tax?.currency ?? defaultCurrency,

      total_amount: draft.total.amount,
      total_currency: draft.total.currency,

      items: draft.items.map((item) => ({
        name: item.name,
        total_price_amount: item.total_price.amount,
        total_price_currency: item.total_price.currency,
        category: item.category,
        bucket: item.bucket,
        quantity: item.quantity,
        unit_price_amount: item.unit_price?.amount ?? null,
        unit_price_currency:
          item.unit_price?.currency ??
          item.total_price.currency,
        confidence: item.confidence,
      })),
    };
  }

  private resetReceipt(): void {
    this.revokePreview();

    this.selectedFile.set(null);
    this.previewUrl.set(null);
    this.draft.set(null);
    this.confirmedReceipt.set(null);
    this.errorMessage.set(null);
    this.isProcessing.set(false);
    this.isConfirming.set(false);
  }

  private revokePreview(): void {
    const currentUrl = this.previewUrl();

    if (currentUrl !== null) {
      URL.revokeObjectURL(currentUrl);
    }
  }

  private describeError(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      return 'The receipt request failed.';
    }

    if (error.status === 0) {
      return 'The backend is unavailable. Check that make dev is running.';
    }

    if (error.status === 404) {
      return 'The original receipt draft could not be found.';
    }

    if (error.status === 409) {
      return 'This receipt draft has already been confirmed.';
    }

    if (error.status === 422) {
      return 'The receipt contains missing or invalid information.';
    }

    if (error.status === 503) {
      return 'The receipt model is starting. Try again in a few seconds.';
    }

    const detail = error.error?.detail;

    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }

    return 'The receipt request failed.';
  }
}
