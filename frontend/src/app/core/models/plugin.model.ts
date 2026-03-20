/** Matches src/api/models/plugin.py */

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  enabled: boolean;
  description: string;
  display_modes: string[];
}

export interface PluginConfigResponse {
  plugin_id: string;
  config: Record<string, unknown>;
  schema: Record<string, unknown>;
}

export interface PluginToggleRequest {
  plugin_id: string;
  enabled: boolean;
}

export interface PluginInstallRequest {
  plugin_id: string;
  source_url: string;
}

/** Store plugin — based on store router response shape */
export interface StorePlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  tags: string[];
  installed: boolean;
}
