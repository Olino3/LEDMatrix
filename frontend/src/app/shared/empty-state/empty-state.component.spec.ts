import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { EmptyStateComponent } from './empty-state.component';

describe('EmptyStateComponent', () => {
  let fixture: ComponentFixture<EmptyStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmptyStateComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();
    fixture = TestBed.createComponent(EmptyStateComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should display the message', () => {
    fixture.componentRef.setInput('message', 'No plugins found');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('No plugins found');
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Nothing here yet');
  });

  it('should show action button when actionLabel is provided', () => {
    fixture.componentRef.setInput('actionLabel', 'Add Plugin');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Add Plugin');
  });

  it('should not show action button when actionLabel is not provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('p-button')).toBeFalsy();
  });

  it('should emit action when action button is clicked', () => {
    fixture.componentRef.setInput('actionLabel', 'Add Plugin');
    fixture.detectChanges();
    const spy = vi.fn();
    fixture.componentInstance.action.subscribe(spy);
    fixture.componentInstance.onAction();
    expect(spy).toHaveBeenCalled();
  });

  it('should render an icon', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-inbox')).toBeTruthy();
  });
});
