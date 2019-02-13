import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ApiService } from '../api/api.service';

const httpOptions = {
  headers: new HttpHeaders({
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  })
};

@Injectable()
export class ItemTypeService {

  constructor(
    private apiService: ApiService,
    private http: HttpClient
  ) { }

  getApiEntryPointRecord(pid: string) {
    return this.apiService
      .getApiEntryPointByType('item_types', true) + pid;
  }

  itemTypes() {
    return this.http.get(
      this.apiService.getApiEntryPointByType('item_types'),
      httpOptions
    );
  }
}
