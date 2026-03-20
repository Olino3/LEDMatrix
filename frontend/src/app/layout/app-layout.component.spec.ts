import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { AppLayoutComponent } from './app-layout.component';

describe('AppLayoutComponent', () => {
  let component: AppLayoutComponent;
  let fixture: ComponentFixture<AppLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppLayoutComponent],
      providers: [provideRouter([]), provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(AppLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have sidebarVisible default to true', () => {
    expect(component.sidebarVisible()).toBe(true);
  });

  it('should toggle sidebarVisible when toggleSidebar is called', () => {
    expect(component.sidebarVisible()).toBe(true);
    component.toggleSidebar();
    expect(component.sidebarVisible()).toBe(false);
    component.toggleSidebar();
    expect(component.sidebarVisible()).toBe(true);
  });

  it('should render the topbar', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('app-topbar')).toBeTruthy();
  });

  it('should render a router-outlet for content', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('router-outlet')).toBeTruthy();
  });
});
