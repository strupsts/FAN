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
import { ReceiptDraftResponse } from '../core/models/receipt.models';

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
  readonly isProcessing = signal(false);
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

  chooseAnother(input: HTMLInputElement): void {
    input.value = '';
    input.click();
  }

  formatMoney(
    money: ReceiptDraftResponse['total'],
  ): string {
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

  private revokePreview(): void {
    const currentUrl = this.previewUrl();

    if (currentUrl !== null) {
      URL.revokeObjectURL(currentUrl);
    }
  }

  private describeError(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      return 'The receipt could not be processed.';
    }

    if (error.status === 0) {
      return 'The backend is unavailable. Check that make dev is running.';
    }

    if (error.status === 422) {
      return 'The selected file is not a supported receipt image.';
    }

    if (error.status === 503) {
      return 'The receipt model is starting. Try again in a few seconds.';
    }

    const detail = error.error?.detail;

    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }

    return 'The receipt could not be processed.';
  }
}
