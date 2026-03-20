import { Injectable, NgZone } from '@angular/core';
import { Observable, share } from 'rxjs';
import { environment } from '../../../environments/environment';
import type {
  StatsEvent,
  DisplayEvent,
  LogEvent,
} from '../models/stream.model';

@Injectable({ providedIn: 'root' })
export class SseService {
  private readonly baseUrl = environment.apiBase;

  constructor(private readonly zone: NgZone) {}

  connect<T>(endpoint: string): Observable<T> {
    return new Observable<T>((subscriber) => {
      const url = `${this.baseUrl}${endpoint}`;
      let eventSource: EventSource;
      let retryCount = 0;
      let retryTimeout: ReturnType<typeof setTimeout> | null = null;

      const createConnection = (): void => {
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
          retryCount = 0;
        };

        eventSource.onmessage = (event: MessageEvent) => {
          this.zone.run(() => {
            try {
              subscriber.next(JSON.parse(event.data) as T);
            } catch {
              // Skip unparseable messages
            }
          });
        };

        eventSource.onerror = () => {
          eventSource.close();
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30_000);
          retryCount++;
          retryTimeout = setTimeout(() => createConnection(), delay);
        };
      };

      createConnection();

      return () => {
        if (retryTimeout !== null) {
          clearTimeout(retryTimeout);
        }
        eventSource?.close();
      };
    });
  }

  readonly statsStream$: Observable<StatsEvent> = this.connect<StatsEvent>(
    '/stream/stats',
  ).pipe(share());

  readonly displayStream$: Observable<DisplayEvent> =
    this.connect<DisplayEvent>('/stream/display').pipe(share());

  readonly logStream$: Observable<LogEvent> = this.connect<LogEvent>(
    '/stream/logs',
  ).pipe(share());
}
