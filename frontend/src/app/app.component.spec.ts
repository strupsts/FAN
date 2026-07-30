import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';
import {
  LocalizationBootstrapService,
} from './core/i18n/localization-bootstrap.service';

describe('AppComponent', () => {
  it('should create the app', async () => {
    const localizationBootstrap =
      jasmine.createSpyObj<LocalizationBootstrapService>(
        'LocalizationBootstrapService',
        ['initialize'],
      );

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([]),
        {
          provide: LocalizationBootstrapService,
          useValue: localizationBootstrap,
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
    expect(
      localizationBootstrap.initialize,
    ).toHaveBeenCalledTimes(1);
  });
});
