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
import {
  ReceiptReviewFormComponent,
} from '../features/receipt-review/receipt-review-form.component';

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

  async confirmReceipt(
    request: ConfirmReceiptRequest,
  ): Promise<void> {
    if (this.isConfirming()) {
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

  ngOnDestroy(): void {
    this.revokePreview();
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
