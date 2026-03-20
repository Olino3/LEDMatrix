import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],
      providers: [provideRouter([]), provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have 5 navigation items', () => {
    expect(component.navItems.length).toBe(5);
  });

  it('should have Dashboard as first item with route /', () => {
    expect(component.navItems[0].label).toBe('Dashboard');
    expect(component.navItems[0].routerLink).toBe('/');
  });

  it('should have Plugins item with route /plugins', () => {
    const item = component.navItems.find((i) => i.label === 'Plugins');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/plugins');
  });

  it('should have Settings item with route /settings', () => {
    const item = component.navItems.find((i) => i.label === 'Settings');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/settings');
  });

  it('should have Logs item with route /logs', () => {
    const item = component.navItems.find((i) => i.label === 'Logs');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/logs');
  });

  it('should have Store item with route /store', () => {
    const item = component.navItems.find((i) => i.label === 'Store');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/store');
  });

  it('should have an icon for each nav item', () => {
    for (const item of component.navItems) {
      expect(item.icon).toBeTruthy();
      expect(item.icon).toMatch(/^pi pi-/);
    }
  });
});
