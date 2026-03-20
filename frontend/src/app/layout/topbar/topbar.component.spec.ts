import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TopbarComponent } from './topbar.component';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

describe('TopbarComponent', () => {
  let component: TopbarComponent;
  let fixture: ComponentFixture<TopbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TopbarComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(TopbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit toggleSidebar when hamburger is clicked', () => {
    const spy = vi.fn();
    component.toggleSidebar.subscribe(spy);
    component.onToggleSidebar();
    expect(spy).toHaveBeenCalled();
  });

  it('should display the app title', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('LEDMatrix');
  });
});
