export interface MoneyResponse {
  amount: string;
  currency: string;
}

export interface ReceiptItemResponse {
  name: string;
  total_price: MoneyResponse;
  category: string;
  bucket: string;
  quantity: number | null;
  unit_price: MoneyResponse | null;
  confidence: number | null;
}

export interface ReceiptDraftResponse {
  id: string;
  merchant_name: string | null;
  purchased_at: string | null;
  subtotal: MoneyResponse | null;
  tax: MoneyResponse | null;
  total: MoneyResponse | null;
  image_ref: string | null;
  extractor_name: string | null;
  items: ReceiptItemResponse[];
}

export interface ReceiptItemConfirmRequest {
  name: string;
  total_price_amount: string;
  total_price_currency: string;
  category: string;
  bucket: string;
  quantity: number | null;
  unit_price_amount: string | null;
  unit_price_currency: string;
  confidence: number | null;
}

export interface ConfirmReceiptRequest {
  draft_id: string;
  merchant_name: string | null;
  purchased_at: string | null;
  image_ref: string | null;
  subtotal_amount: string | null;
  subtotal_currency: string;
  tax_amount: string | null;
  tax_currency: string;
  total_amount: string;
  total_currency: string;
  items: ReceiptItemConfirmRequest[];
}

export interface ConfirmedReceiptResponse {
  id: string;
  user_id: string;
  merchant_name: string | null;
  purchased_at: string | null;
  subtotal: MoneyResponse | null;
  tax: MoneyResponse | null;
  total: MoneyResponse;
  image_ref: string | null;
  items: ReceiptItemResponse[];
}
