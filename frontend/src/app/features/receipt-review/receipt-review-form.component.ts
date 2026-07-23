import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  signal,
  SimpleChanges,
} from '@angular/core';
import {
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonInput,
  IonSelect,
  IonSelectOption,
  IonSpinner,
} from '@ionic/angular/standalone';

import {
  ConfirmReceiptRequest,
  ReceiptDraftResponse,
  ReceiptItemResponse,
} from '../../core/models/receipt.models';
import {
  BUDGET_BUCKET_OPTIONS,
  RECEIPT_CATEGORY_OPTIONS,
} from './receipt-review.options';

const MONEY_PATTERN = /^-?\d+(?:\.\d{1,2})?$/;
const NON_NEGATIVE_MONEY_PATTERN = /^\d+(?:\.\d{1,2})?$/;
const QUANTITY_PATTERN = /^\d+(?:\.\d+)?$/;

type ReceiptItemFormGroup = FormGroup<{
  name: FormControl<string>;
  quantity: FormControl<string>;
  unit_price_amount: FormControl<string>;
  unit_price_currency: FormControl<string>;
  total_price_amount: FormControl<string>;
  total_price_currency: FormControl<string>;
  category: FormControl<string>;
  bucket: FormControl<string>;
  confidence: FormControl<number | null>;
}>;

type ReceiptReviewFormGroup = FormGroup<{
  merchant_name: FormControl<string>;
  purchased_at: FormControl<string>;
  subtotal_amount: FormControl<string>;
  subtotal_currency: FormControl<string>;
  tax_amount: FormControl<string>;
  tax_currency: FormControl<string>;
  total_amount: FormControl<string>;
  total_currency: FormControl<string>;
  items: FormArray<ReceiptItemFormGroup>;
}>;

@Component({
  selector: 'app-receipt-review-form',
  templateUrl: './receipt-review-form.component.html',
  styleUrls: ['./receipt-review-form.component.scss'],
  imports: [
    ReactiveFormsModule,
    IonButton,
    IonCard,
    IonCardContent,
    IonInput,
    IonSelect,
    IonSelectOption,
    IonSpinner,
  ],
})
export class ReceiptReviewFormComponent implements OnChanges {
  @Input({ required: true })
  draft!: ReceiptDraftResponse;

  @Input()
  isSubmitting = false;

  @Output()
  readonly confirmRequested =
    new EventEmitter<ConfirmReceiptRequest>();

  readonly categoryOptions = RECEIPT_CATEGORY_OPTIONS;
  readonly bucketOptions = BUDGET_BUCKET_OPTIONS;
  readonly showValidationErrors = signal(false);

  readonly form: ReceiptReviewFormGroup = new FormGroup({
    merchant_name: new FormControl('', {
      nonNullable: true,
    }),
    purchased_at: new FormControl('', {
      nonNullable: true,
    }),
    subtotal_amount: new FormControl('', {
      nonNullable: true,
      validators: [Validators.pattern(MONEY_PATTERN)],
    }),
    subtotal_currency: new FormControl('CAD', {
      nonNullable: true,
    }),
    tax_amount: new FormControl('', {
      nonNullable: true,
      validators: [Validators.pattern(MONEY_PATTERN)],
    }),
    tax_currency: new FormControl('CAD', {
      nonNullable: true,
    }),
    total_amount: new FormControl('', {
      nonNullable: true,
      validators: [
        Validators.required,
        Validators.pattern(NON_NEGATIVE_MONEY_PATTERN),
      ],
    }),
    total_currency: new FormControl('CAD', {
      nonNullable: true,
    }),
    items: new FormArray<ReceiptItemFormGroup>([]),
  });

  get items(): FormArray<ReceiptItemFormGroup> {
    return this.form.controls.items;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['draft'] !== undefined && this.draft !== undefined) {
      this.loadDraft(this.draft);
    }
  }

  addItem(): void {
    const currency =
      this.form.controls.total_currency.value || 'CAD';

    this.items.push(this.createItemGroup(null, currency));
  }

  removeItem(index: number): void {
    if (this.items.length <= 1) {
      return;
    }

    this.items.removeAt(index);
  }

  submit(): void {
    if (this.isSubmitting) {
      return;
    }

    this.showValidationErrors.set(true);
    this.form.markAllAsTouched();

    if (this.form.invalid || this.items.length === 0) {
      return;
    }

    const value = this.form.getRawValue();

    this.confirmRequested.emit({
      draft_id: this.draft.id,
      merchant_name: this.emptyToNull(value.merchant_name),
      purchased_at: this.emptyToNull(value.purchased_at),
      image_ref: this.draft.image_ref,

      subtotal_amount:
        this.emptyToNull(value.subtotal_amount),
      subtotal_currency: value.subtotal_currency,

      tax_amount: this.emptyToNull(value.tax_amount),
      tax_currency: value.tax_currency,

      total_amount: value.total_amount.trim(),
      total_currency: value.total_currency,

      items: value.items.map((item) => {
        const quantity = item.quantity.trim();

        return {
          name: item.name.trim(),
          quantity:
            quantity === ''
              ? null
              : Number(quantity),
          unit_price_amount:
            this.emptyToNull(item.unit_price_amount),
          unit_price_currency: item.unit_price_currency,
          total_price_amount:
            item.total_price_amount.trim(),
          total_price_currency:
            item.total_price_currency,
          category: item.category,
          bucket: item.bucket,
          confidence: item.confidence,
        };
      }),
    });
  }

  private loadDraft(draft: ReceiptDraftResponse): void {
    const currency =
      draft.total?.currency ??
      draft.subtotal?.currency ??
      draft.tax?.currency ??
      'CAD';

    this.form.controls.merchant_name.setValue(
      draft.merchant_name ?? '',
    );
    this.form.controls.purchased_at.setValue(
      this.toDateTimeLocal(draft.purchased_at),
    );

    this.form.controls.subtotal_amount.setValue(
      draft.subtotal?.amount ?? '',
    );
    this.form.controls.subtotal_currency.setValue(
      draft.subtotal?.currency ?? currency,
    );

    this.form.controls.tax_amount.setValue(
      draft.tax?.amount ?? '',
    );
    this.form.controls.tax_currency.setValue(
      draft.tax?.currency ?? currency,
    );

    this.form.controls.total_amount.setValue(
      draft.total?.amount ?? '',
    );
    this.form.controls.total_currency.setValue(
      draft.total?.currency ?? currency,
    );

    this.items.clear();

    for (const item of draft.items) {
      this.items.push(
        this.createItemGroup(item, currency),
      );
    }

    if (this.items.length === 0) {
      this.addItem();
    }

    this.form.markAsPristine();
    this.form.markAsUntouched();
    this.showValidationErrors.set(false);
  }

  private createItemGroup(
    item: ReceiptItemResponse | null,
    currency: string,
  ): ReceiptItemFormGroup {
    return new FormGroup({
      name: new FormControl(item?.name ?? '', {
        nonNullable: true,
        validators: [Validators.required],
      }),
      quantity: new FormControl(
        item?.quantity?.toString() ?? '',
        {
          nonNullable: true,
          validators: [
            Validators.pattern(QUANTITY_PATTERN),
          ],
        },
      ),
      unit_price_amount: new FormControl(
        item?.unit_price?.amount ?? '',
        {
          nonNullable: true,
          validators: [
            Validators.pattern(MONEY_PATTERN),
          ],
        },
      ),
      unit_price_currency: new FormControl(
        item?.unit_price?.currency ?? currency,
        {
          nonNullable: true,
        },
      ),
      total_price_amount: new FormControl(
        item?.total_price.amount ?? '',
        {
          nonNullable: true,
          validators: [
            Validators.required,
            Validators.pattern(MONEY_PATTERN),
          ],
        },
      ),
      total_price_currency: new FormControl(
        item?.total_price.currency ?? currency,
        {
          nonNullable: true,
        },
      ),
      category: new FormControl(
        item?.category ?? 'unknown',
        {
          nonNullable: true,
          validators: [Validators.required],
        },
      ),
      bucket: new FormControl(
        item?.bucket ?? 'unknown',
        {
          nonNullable: true,
          validators: [Validators.required],
        },
      ),
      confidence: new FormControl<number | null>(
        item?.confidence ?? null,
      ),
    });
  }

  private emptyToNull(value: string): string | null {
    const normalized = value.trim();

    return normalized === '' ? null : normalized;
  }

  private toDateTimeLocal(value: string | null): string {
    if (value === null) {
      return '';
    }

    const match = value.match(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/,
    );

    return match?.[0] ?? '';
  }
}
