import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoadingComponent } from './loading.component';

describe('LoadingComponent', () => {
  let fixture: ComponentFixture<LoadingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoadingComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LoadingComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.loading-message')?.textContent?.trim()).toBe('Loading...');
  });

  it('should show custom message when provided', () => {
    fixture.componentRef.setInput('message', 'Fetching plugins');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.loading-message')?.textContent?.trim()).toBe('Fetching plugins');
  });

  it('should render a spinner element', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-spin')).toBeTruthy();
  });
});
