import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ConfirmedReceiptResponse,
  ConfirmReceiptRequest,
  ReceiptDraftResponse,
} from '../models/receipt.models';

@Injectable({
  providedIn: 'root',
})
export class ReceiptApiService {
  private readonly http = inject(HttpClient);

  processReceipt(file: File): Observable<ReceiptDraftResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);

    return this.http.post<ReceiptDraftResponse>(
      `${environment.apiBaseUrl}/api/receipts/process`,
      formData,
    );
  }

  confirmReceipt(
    request: ConfirmReceiptRequest,
  ): Observable<ConfirmedReceiptResponse> {
    return this.http.post<ConfirmedReceiptResponse>(
      `${environment.apiBaseUrl}/api/receipts/confirm`,
      request,
    );
  }
}
