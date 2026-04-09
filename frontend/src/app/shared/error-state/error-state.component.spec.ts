import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ErrorStateComponent } from './error-state.component';

describe('ErrorStateComponent', () => {
  let fixture: ComponentFixture<ErrorStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ErrorStateComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();
    fixture = TestBed.createComponent(ErrorStateComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should display the error message', () => {
    fixture.componentRef.setInput('message', 'Something went wrong');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Something went wrong');
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('An error occurred');
  });

  it('should emit retry when retry button is clicked', () => {
    fixture.detectChanges();
    const spy = vi.fn();
    fixture.componentInstance.retry.subscribe(spy);
    fixture.componentInstance.onRetry();
    expect(spy).toHaveBeenCalled();
  });

  it('should render an error icon', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-exclamation-circle')).toBeTruthy();
  });
});
