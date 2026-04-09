import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

export interface NavItem {
  label: string;
  icon: string;
  routerLink: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'pi pi-home', routerLink: '/' },
    { label: 'Plugins', icon: 'pi pi-th-large', routerLink: '/plugins' },
    { label: 'Settings', icon: 'pi pi-cog', routerLink: '/settings' },
    { label: 'Logs', icon: 'pi pi-list', routerLink: '/logs' },
    { label: 'Store', icon: 'pi pi-shopping-bag', routerLink: '/store' },
  ];
}
