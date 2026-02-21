/**
 * Web platform implementation
 * Provides web-compatible implementations of platform interfaces
 */

import type {
  Platform,
  PlatformFilesystem,
  PlatformUpdater,
  PlatformAudio,
  PlatformLifecycle,
  PlatformMetadata,
  UpdateStatus,
  AudioDevice,
  FileFilter,
} from './types';

// Web filesystem implementation - uses browser download
const webFilesystem: PlatformFilesystem = {
  async saveFile(filename: string, blob: Blob, _filters?: FileFilter[]): Promise<void> {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// Web updater - no-op for web deployments
const webUpdater: PlatformUpdater = {
  async checkForUpdates(): Promise<void> {
    // Web apps update automatically via deployment
  },
  async downloadAndInstall(): Promise<void> {
    // No-op for web
  },
  async restartAndInstall(): Promise<void> {
    // Reload the page to get latest version
    window.location.reload();
  },
  getStatus(): UpdateStatus {
    return {
      checking: false,
      available: false,
      downloading: false,
      installing: false,
      readyToInstall: false,
    };
  },
  subscribe(_callback: (status: UpdateStatus) => void): () => void {
    // No updates to subscribe to on web
    return () => {};
  },
};

// Web audio - limited capabilities
const webAudio: PlatformAudio = {
  isSystemAudioSupported(): boolean {
    return false; // System audio capture not supported on web
  },
  async startSystemAudioCapture(_maxDurationSecs: number): Promise<void> {
    throw new Error('System audio capture not supported on web');
  },
  async stopSystemAudioCapture(): Promise<Blob> {
    throw new Error('System audio capture not supported on web');
  },
  async listOutputDevices(): Promise<AudioDevice[]> {
    // Web can only list devices if user grants permission
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices
        .filter(d => d.kind === 'audiooutput')
        .map((d, i) => ({
          id: d.deviceId || `device-${i}`,
          name: d.label || `Speaker ${i + 1}`,
          is_default: d.deviceId === 'default',
        }));
    } catch {
      return [{ id: 'default', name: 'Default Speaker', is_default: true }];
    }
  },
  async playToDevices(_audioData: Uint8Array, _deviceIds: string[]): Promise<void> {
    // Web doesn't support multi-device output easily
    throw new Error('Multi-device playback not supported on web');
  },
  stopPlayback(): void {
    // No-op
  },
};

// Web lifecycle - server is already running remotely
const webLifecycle: PlatformLifecycle = {
  async startServer(_remote?: boolean): Promise<string> {
    // Server is already running (Railway), return the URL from env or default
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:17493';
    return apiUrl;
  },
  async stopServer(): Promise<void> {
    // Can't stop remote server from web
  },
  async setKeepServerRunning(_keep: boolean): Promise<void> {
    // No-op for web
  },
  async setupWindowCloseHandler(): Promise<void> {
    // No-op for web
  },
  onServerReady: undefined,
};

// Web metadata
const webMetadata: PlatformMetadata = {
  async getVersion(): Promise<string> {
    return '1.0.0-web';
  },
  isTauri: false,
};

export const webPlatform: Platform = {
  filesystem: webFilesystem,
  updater: webUpdater,
  audio: webAudio,
  lifecycle: webLifecycle,
  metadata: webMetadata,
};
