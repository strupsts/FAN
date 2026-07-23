export interface ReceiptSelectOption {
  value: string;
  label: string;
}

export const RECEIPT_CATEGORY_OPTIONS: readonly ReceiptSelectOption[] = [
  { value: 'groceries', label: 'Groceries' },
  { value: 'restaurants', label: 'Restaurants' },
  { value: 'transport', label: 'Transport' },
  { value: 'auto', label: 'Auto' },
  { value: 'household', label: 'Household' },
  { value: 'health', label: 'Health' },
  { value: 'personal_care', label: 'Personal care' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'clothing', label: 'Clothing' },
  { value: 'electronics', label: 'Electronics' },
  { value: 'tools', label: 'Tools' },
  { value: 'fees', label: 'Fees' },
  { value: 'tax', label: 'Tax' },
  { value: 'discount', label: 'Discount' },
  { value: 'other', label: 'Other' },
  { value: 'unknown', label: 'Unknown' },
];

export const BUDGET_BUCKET_OPTIONS: readonly ReceiptSelectOption[] = [
  { value: 'needs', label: 'Needs' },
  { value: 'wants', label: 'Wants' },
  { value: 'savings', label: 'Savings' },
  { value: 'debt', label: 'Debt' },
  { value: 'unknown', label: 'Unknown' },
];
