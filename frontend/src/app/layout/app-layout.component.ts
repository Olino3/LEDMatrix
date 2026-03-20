import { Component, signal, HostListener } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DrawerModule } from 'primeng/drawer';
import { TopbarComponent } from './topbar/topbar.component';
import { SidebarComponent } from './sidebar/sidebar.component';

const MOBILE_BREAKPOINT = 768;

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [RouterOutlet, DrawerModule, TopbarComponent, SidebarComponent],
  templateUrl: './app-layout.component.html',
  styleUrl: './app-layout.component.scss',
})
export class AppLayoutComponent {
  sidebarVisible = signal(true);
  isMobile = signal(false);

  constructor() {
    this.checkMobile();
  }

  toggleSidebar(): void {
    this.sidebarVisible.update((v) => !v);
  }

  @HostListener('window:resize')
  onResize(): void {
    this.checkMobile();
  }

  private checkMobile(): void {
    if (typeof window !== 'undefined') {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      this.isMobile.set(mobile);
      if (mobile) {
        this.sidebarVisible.set(false);
      }
    }
  }
}
