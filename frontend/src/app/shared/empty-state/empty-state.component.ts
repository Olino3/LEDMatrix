import { Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [ButtonModule],
  templateUrl: './empty-state.component.html',
  styleUrl: './empty-state.component.scss',
})
export class EmptyStateComponent {
  icon = input('pi pi-inbox');
  message = input('Nothing here yet');
  actionLabel = input<string | undefined>(undefined);
  action = output<void>();

  onAction(): void {
    this.action.emit();
  }
}
