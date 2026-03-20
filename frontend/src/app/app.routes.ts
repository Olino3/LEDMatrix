import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./layout/app-layout.component').then((m) => m.AppLayoutComponent),
    children: [
      // Feature modules will be lazy-loaded here in FRONT-004/005/006
    ],
  },
];
