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
