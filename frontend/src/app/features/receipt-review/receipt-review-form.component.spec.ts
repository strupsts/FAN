import {
  ComponentFixture,
  TestBed,
} from '@angular/core/testing';

import {
  ConfirmReceiptRequest,
  ReceiptDraftResponse,
} from '../../core/models/receipt.models';
import {
  ReceiptReviewFormComponent,
} from './receipt-review-form.component';

describe('ReceiptReviewFormComponent', () => {
  let component: ReceiptReviewFormComponent;
  let fixture: ComponentFixture<ReceiptReviewFormComponent>;

  const draft: ReceiptDraftResponse = {
    id: 'draft-1',
    merchant_name: 'Detected Store',
    purchased_at: '2026-07-23T09:30:00',
    subtotal: {
      amount: '10.00',
      currency: 'CAD',
    },
    tax: {
      amount: '0.50',
      currency: 'CAD',
    },
    total: {
      amount: '10.50',
      currency: 'CAD',
    },
    image_ref: 'local://receipt.jpg',
    extractor_name: 'test-extractor',
    items: [
      {
        name: 'Detected Item',
        total_price: {
          amount: '10.00',
          currency: 'CAD',
        },
        category: 'groceries',
        bucket: 'needs',
        quantity: 1,
        unit_price: {
          amount: '10.00',
          currency: 'CAD',
        },
        confidence: 0.9,
      },
    ],
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReceiptReviewFormComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(
      ReceiptReviewFormComponent,
    );
    component = fixture.componentInstance;

    fixture.componentRef.setInput('draft', draft);
    fixture.detectChanges();
  });

  it('loads the detected draft into the form', () => {
    expect(
      component.form.controls.merchant_name.value,
    ).toBe('Detected Store');

    expect(component.items.length).toBe(1);

    expect(
      component.items.at(0).controls.name.value,
    ).toBe('Detected Item');
  });

  it('recalculates totals after adding an item', () => {
    component.addItem();

    component.items
      .at(1)
      .controls.name
      .setValue('Added Item');

    component.items
      .at(1)
      .controls.total_price_amount
      .setValue('7.80');

    component.recalculateTotals();

    expect(
      component.form.controls.subtotal_amount.value,
    ).toBe('17.80');

    expect(
      component.form.controls.total_amount.value,
    ).toBe('18.30');
  });

  it('emits corrected calculated totals', () => {
    let emitted:
      | ConfirmReceiptRequest
      | undefined;

    component.confirmRequested.subscribe((request) => {
      emitted = request;
    });

    component.form.controls.merchant_name.setValue(
      'Corrected Store',
    );

    component.items
      .at(0)
      .controls.name
      .setValue('Corrected Item');

    component.items
      .at(0)
      .controls.total_price_amount
      .setValue('12.34');

    component.recalculateTotals();
    component.submit();

    expect(emitted?.merchant_name).toBe(
      'Corrected Store',
    );

    expect(emitted?.subtotal_amount).toBe('12.34');
    expect(emitted?.total_amount).toBe('12.84');

    expect(emitted?.items[0].name).toBe(
      'Corrected Item',
    );
  });

});
