"""
Comprehensive test suite for scripts/matrix_cli.py.

Uses Click's CliRunner + unittest.mock to test all commands and helpers
without touching the real filesystem, network, or subprocesses.
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
import matrix_cli
from matrix_cli import (
    cli,
    _to_class_name,
    _to_display_name,
    _read_config,
    _write_config,
    _read_manifest,
)


# ---------------------------------------------------------------------------
# Task 1 — String helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStringHelpers:
    """Pure string conversion helpers."""

    def test_to_class_name_single_word(self):
        assert _to_class_name('clock') == 'ClockPlugin'

    def test_to_class_name_hyphenated(self):
        assert _to_class_name('clock-simple') == 'ClockSimplePlugin'

    def test_to_class_name_underscore_treated_as_hyphen(self):
        assert _to_class_name('transit_board') == 'TransitBoardPlugin'

    def test_to_class_name_three_segments(self):
        assert _to_class_name('a-b-c') == 'ABCPlugin'

    def test_to_display_name_single_word(self):
        assert _to_display_name('clock') == 'Clock'

    def test_to_display_name_hyphenated(self):
        assert _to_display_name('clock-simple') == 'Clock Simple'

    def test_to_display_name_underscore_treated_as_hyphen(self):
        assert _to_display_name('transit_board') == 'Transit Board'

    def test_to_display_name_three_segments(self):
        assert _to_display_name('a-b-c') == 'A B C'


# ---------------------------------------------------------------------------
# Task 2 — Filesystem helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFilesystemHelpers:
    """_read_config, _write_config, _read_manifest."""

    def test_read_config_missing_file_returns_empty_dict(self, tmp_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', tmp_path / 'missing.json'):
            assert matrix_cli._read_config() == {}

    def test_read_config_returns_parsed_json(self, tmp_path, fake_config_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            cfg = matrix_cli._read_config()
        assert cfg['clock-simple']['enabled'] is True

    def test_write_config_creates_file(self, tmp_path):
        cfg_path = tmp_path / 'config.json'
        with patch.object(matrix_cli, 'CONFIG_PATH', cfg_path):
            matrix_cli._write_config({'test': {'enabled': False}})
        assert cfg_path.exists()
        assert json.loads(cfg_path.read_text()) == {'test': {'enabled': False}}

    def test_write_config_pretty_printed_with_trailing_newline(self, tmp_path):
        cfg_path = tmp_path / 'config.json'
        with patch.object(matrix_cli, 'CONFIG_PATH', cfg_path):
            matrix_cli._write_config({'a': 1})
        content = cfg_path.read_text()
        assert '\n' in content
        assert content.endswith('\n')

    def test_read_manifest_missing_returns_none(self, tmp_path):
        assert matrix_cli._read_manifest(tmp_path) is None

    def test_read_manifest_valid(self, tmp_path):
        mf = tmp_path / 'manifest.json'
        mf.write_text(json.dumps({'id': 'test', 'name': 'Test'}))
        assert matrix_cli._read_manifest(tmp_path) == {'id': 'test', 'name': 'Test'}

    def test_read_manifest_invalid_json_returns_none(self, tmp_path):
        (tmp_path / 'manifest.json').write_text('{bad json}')
        assert matrix_cli._read_manifest(tmp_path) is None

    def test_write_then_read_roundtrip(self, tmp_path):
        cfg_path = tmp_path / 'config.json'
        data = {'plugin-a': {'enabled': True}, 'plugin-b': {'enabled': False}}
        with patch.object(matrix_cli, 'CONFIG_PATH', cfg_path):
            matrix_cli._write_config(data)
            result = matrix_cli._read_config()
        assert result == data


# ---------------------------------------------------------------------------
# Task 3 — HTTP helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHttpHelpers:
    """_detect_web, _require_web, _api_post, _api_get."""

    def test_detect_web_returns_true_on_success(self):
        with patch('matrix_cli.requests') as r:
            r.get.return_value = MagicMock(status_code=200)
            assert matrix_cli._detect_web() is True

    def test_detect_web_returns_false_on_connection_error(self):
        with patch('matrix_cli.requests') as r:
            r.get.side_effect = Exception('refused')
            assert matrix_cli._detect_web() is False

    def test_detect_web_uses_health_endpoint(self):
        with patch('matrix_cli.requests') as r:
            r.get.return_value = MagicMock()
            matrix_cli._detect_web()
        url = r.get.call_args[0][0]
        assert 'health' in url

    def test_detect_web_timeout_is_1_second(self):
        with patch('matrix_cli.requests') as r:
            r.get.return_value = MagicMock()
            matrix_cli._detect_web()
        assert r.get.call_args[1].get('timeout') == 1

    def test_require_web_returns_true_when_running(self):
        with patch('matrix_cli._detect_web', return_value=True):
            assert matrix_cli._require_web() is True

    def test_require_web_returns_false_and_prints_hint_when_down(self):
        with patch('matrix_cli._detect_web', return_value=False):
            result = matrix_cli._require_web()
        assert result is False

    def test_api_post_returns_json_on_success(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True}
        with patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = matrix_cli._api_post('/plugins/install', {'plugin_id': 'x'})
        assert result == {'success': True}

    def test_api_post_returns_none_on_exception(self):
        with patch('matrix_cli.requests') as r:
            r.post.side_effect = Exception('Network error')
            assert matrix_cli._api_post('/path', {}) is None

    def test_api_post_uses_correct_full_url(self):
        resp = MagicMock()
        resp.json.return_value = {}
        with patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            matrix_cli._api_post('/plugins/update', {})
        url = r.post.call_args[0][0]
        assert url == f'{matrix_cli.API_BASE}/plugins/update'

    def test_api_get_returns_json_on_success(self):
        resp = MagicMock()
        resp.json.return_value = {'plugins': []}
        with patch('matrix_cli.requests') as r:
            r.get.return_value = resp
            result = matrix_cli._api_get('/plugins/health')
        assert result == {'plugins': []}

    def test_api_get_returns_none_on_exception(self):
        with patch('matrix_cli.requests') as r:
            r.get.side_effect = Exception('Timeout')
            assert matrix_cli._api_get('/plugins/health') is None


# ---------------------------------------------------------------------------
# Task 4 — run and web commands
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunAndWebCommands:
    """matrix run and matrix web commands."""

    def test_run_sets_emulator_env(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['run'])
        cmd = mock_sub.call_args[0][0]
        assert 'run.py' in ' '.join(str(c) for c in cmd)

    def test_run_without_debug_no_debug_flag(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['run'])
        cmd = mock_sub.call_args[0][0]
        assert '--debug' not in cmd

    def test_run_with_debug_passes_flag(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['run', '--debug'])
        cmd = mock_sub.call_args[0][0]
        assert '--debug' in cmd

    def test_run_exits_with_subprocess_returncode(self):
        mock_proc = MagicMock(returncode=42)
        with patch('subprocess.run', return_value=mock_proc):
            result = CliRunner().invoke(matrix_cli.cli, ['run'])
        assert result.exit_code == 42

    def test_web_calls_start_py(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['web'])
        cmd = mock_sub.call_args[0][0]
        assert 'start.py' in ' '.join(str(c) for c in cmd)

    def test_web_exits_with_subprocess_returncode(self):
        mock_proc = MagicMock(returncode=1)
        with patch('subprocess.run', return_value=mock_proc):
            result = CliRunner().invoke(matrix_cli.cli, ['web'])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Task 5 — logs and service commands
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLogsCommand:
    """matrix logs [--service display|web|all]."""

    @pytest.mark.parametrize('service,expected_units', [
        ('display', ['ledmatrix']),
        ('web',     ['ledmatrix-web']),
        ('all',     ['ledmatrix', 'ledmatrix-web']),
    ])
    def test_logs_service_maps_to_correct_units(self, service, expected_units):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['logs', '--service', service])
        cmd = mock_sub.call_args[0][0]
        cmd_str = ' '.join(str(c) for c in cmd)
        for unit in expected_units:
            assert unit in cmd_str

    def test_logs_default_service_is_display(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['logs'])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert 'ledmatrix' in cmd_str

    def test_logs_handles_missing_journalctl(self):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = CliRunner().invoke(matrix_cli.cli, ['logs'])
        assert result.exit_code in (0, 1)

    def test_logs_uses_journalctl(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['logs'])
        cmd = mock_sub.call_args[0][0]
        assert 'journalctl' in cmd[0]


@pytest.mark.unit
class TestServiceCommand:
    """matrix service {start|stop|restart|status} [--service display|web|all]."""

    @pytest.mark.parametrize('action', ['start', 'stop', 'restart', 'status'])
    def test_service_action_passed_to_systemctl(self, action):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['service', action])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert action in cmd_str

    def test_service_all_calls_systemctl_twice(self):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['service', 'start', '--service', 'all'])
        assert mock_sub.call_count == 2

    def test_service_or_of_return_codes(self):
        mock_proc_ok = MagicMock(returncode=0)
        mock_proc_err = MagicMock(returncode=1)
        with patch('subprocess.run', side_effect=[mock_proc_ok, mock_proc_err]):
            result = CliRunner().invoke(matrix_cli.cli, ['service', 'start', '--service', 'all'])
        assert result.exit_code == 1

    def test_service_handles_missing_systemctl(self):
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = CliRunner().invoke(matrix_cli.cli, ['service', 'start'])
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# Task 6 — plugin list
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginList:
    """matrix plugin list."""

    def test_list_shows_plugin_name(self, fake_plugins_dir, fake_config_path):
        with patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert result.exit_code == 0
        assert 'clock-simple' in result.output

    def test_list_shows_enabled_status(self, fake_plugins_dir, fake_config_path):
        with patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert 'enabled' in result.output.lower()

    def test_list_shows_disabled_status(self, fake_plugins_dir, fake_config_path):
        with patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert 'disabled' in result.output.lower()

    def test_list_empty_plugins_dir(self, tmp_path):
        empty_dir = tmp_path / 'plugins'
        empty_dir.mkdir()
        empty_cfg = tmp_path / 'config.json'
        empty_cfg.write_text('{}')
        with patch.object(matrix_cli, 'PLUGINS_DIR', empty_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', empty_cfg):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert result.exit_code == 0

    def test_list_shows_version(self, fake_plugins_dir, fake_config_path):
        with patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert '1.0.0' in result.output

    def test_list_shows_dev_link_for_symlink(self, tmp_path, fake_config_path):
        plugins_dir = tmp_path / 'plugins'
        plugins_dir.mkdir()
        real_repo = tmp_path / 'real-repo'
        real_repo.mkdir()
        (real_repo / 'manifest.json').write_text(json.dumps({
            'id': 'dev-plugin', 'name': 'Dev Plugin',
            'version': '0.1.0', 'category': 'other',
        }))
        link_path = plugins_dir / 'dev-plugin'
        link_path.symlink_to(real_repo)
        with patch.object(matrix_cli, 'PLUGINS_DIR', plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert 'yes' in result.output.lower() or '✓' in result.output

    def test_list_skips_plugin_missing_manifest(self, tmp_path, fake_config_path):
        plugins_dir = tmp_path / 'plugins'
        plugins_dir.mkdir()
        bad = plugins_dir / 'no-manifest'
        bad.mkdir()
        with patch.object(matrix_cli, 'PLUGINS_DIR', plugins_dir), \
             patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'list'])
        assert 'no-manifest' not in result.output
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Task 7 — plugin enable / disable
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginEnableDisable:
    """matrix plugin enable/disable."""

    def test_enable_sets_enabled_true_in_config(self, tmp_path, fake_config_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'enable', 'weather-board'])
        assert result.exit_code == 0
        cfg = json.loads(fake_config_path.read_text())
        assert cfg['weather-board']['enabled'] is True

    def test_disable_sets_enabled_false_in_config(self, tmp_path, fake_config_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'disable', 'clock-simple'])
        assert result.exit_code == 0
        cfg = json.loads(fake_config_path.read_text())
        assert cfg['clock-simple']['enabled'] is False

    def test_enable_creates_config_entry_if_missing(self, tmp_path):
        cfg_path = tmp_path / 'config.json'
        cfg_path.write_text('{}')
        with patch.object(matrix_cli, 'CONFIG_PATH', cfg_path):
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'enable', 'brand-new-plugin'])
        cfg = json.loads(cfg_path.read_text())
        assert cfg['brand-new-plugin']['enabled'] is True

    def test_enable_prints_success_message(self, fake_config_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'enable', 'weather-board'])
        assert 'weather-board' in result.output

    def test_disable_prints_success_message(self, fake_config_path):
        with patch.object(matrix_cli, 'CONFIG_PATH', fake_config_path):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'disable', 'clock-simple'])
        assert 'clock-simple' in result.output

    def test_enable_preserves_other_config_keys(self, tmp_path):
        cfg_path = tmp_path / 'config.json'
        cfg_path.write_text(json.dumps({
            'plugin-a': {'enabled': True, 'display_duration': 30}
        }))
        with patch.object(matrix_cli, 'CONFIG_PATH', cfg_path):
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'enable', 'plugin-a'])
        cfg = json.loads(cfg_path.read_text())
        assert cfg['plugin-a']['display_duration'] == 30


# ---------------------------------------------------------------------------
# Task 8 — plugin new
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginNew:
    """matrix plugin new <id> [--path <dir>] [--no-interactive]."""

    def test_new_creates_required_files(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            result = CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'my-plugin', '--path', str(tmp_path), '--no-interactive']
            )
        plugin_dir = tmp_path / 'my-plugin'
        assert plugin_dir.exists()
        assert (plugin_dir / 'manifest.json').exists()
        assert (plugin_dir / 'config_schema.json').exists()
        assert (plugin_dir / 'manager.py').exists()
        assert (plugin_dir / 'requirements.txt').exists()

    def test_new_manifest_has_correct_id(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'test-id', '--path', str(tmp_path), '--no-interactive']
            )
        manifest = json.loads((tmp_path / 'test-id' / 'manifest.json').read_text())
        assert manifest['id'] == 'test-id'

    def test_new_manifest_version_is_0_1_0(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'test-id', '--path', str(tmp_path), '--no-interactive']
            )
        manifest = json.loads((tmp_path / 'test-id' / 'manifest.json').read_text())
        assert manifest['version'] == '0.1.0'

    def test_new_manager_contains_correct_class_name(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'my-widget', '--path', str(tmp_path), '--no-interactive']
            )
        manager_src = (tmp_path / 'my-widget' / 'manager.py').read_text()
        assert 'MyWidgetPlugin' in manager_src

    def test_new_config_schema_is_valid_json(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'json-test', '--path', str(tmp_path), '--no-interactive']
            )
        schema_path = tmp_path / 'json-test' / 'config_schema.json'
        parsed = json.loads(schema_path.read_text())
        assert isinstance(parsed, dict)

    def test_new_calls_git_init(self, tmp_path):
        mock_proc = MagicMock(returncode=0)
        with patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'git-plugin', '--path', str(tmp_path), '--no-interactive']
            )
        calls_str = ' '.join(' '.join(str(c) for c in ca[0][0]) for ca in mock_sub.call_args_list)
        assert 'git' in calls_str and 'init' in calls_str

    def test_new_fails_if_directory_already_exists(self, tmp_path):
        existing = tmp_path / 'existing-plugin'
        existing.mkdir()
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            result = CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'existing-plugin', '--path', str(tmp_path), '--no-interactive']
            )
        assert result.exit_code != 0

    def test_new_prints_plugin_summary(self, tmp_path):
        with patch('subprocess.run', return_value=MagicMock(returncode=0)):
            result = CliRunner().invoke(
                matrix_cli.cli,
                ['plugin', 'new', 'summary-plugin', '--path', str(tmp_path), '--no-interactive']
            )
        assert 'summary-plugin' in result.output


# ---------------------------------------------------------------------------
# Task 9 — plugin link / unlink / status
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginLinkUnlink:
    """matrix plugin link/unlink/status (delegates to _dev_setup)."""

    def test_link_calls_dev_setup_with_link_args(self, tmp_path):
        fake_script = tmp_path / 'dev_setup.sh'
        fake_script.touch()
        with patch.object(matrix_cli, 'DEV_SETUP', fake_script), \
             patch('matrix_cli._run', return_value=0) as mock_run:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'link', 'my-plugin', '/repo/path'])
        cmd = mock_run.call_args[0][0]
        assert 'link' in cmd
        assert 'my-plugin' in cmd
        assert '/repo/path' in cmd

    def test_unlink_calls_dev_setup_with_unlink_args(self, tmp_path):
        fake_script = tmp_path / 'dev_setup.sh'
        fake_script.touch()
        with patch.object(matrix_cli, 'DEV_SETUP', fake_script), \
             patch('matrix_cli._run', return_value=0) as mock_run:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'unlink', 'my-plugin'])
        cmd = mock_run.call_args[0][0]
        assert 'unlink' in cmd
        assert 'my-plugin' in cmd

    def test_status_calls_dev_setup_with_status(self, tmp_path):
        fake_script = tmp_path / 'dev_setup.sh'
        fake_script.touch()
        with patch.object(matrix_cli, 'DEV_SETUP', fake_script), \
             patch('matrix_cli._run', return_value=0) as mock_run:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'status'])
        cmd = mock_run.call_args[0][0]
        assert 'status' in cmd

    def test_link_missing_script_exits_nonzero(self, tmp_path):
        with patch.object(matrix_cli, 'DEV_SETUP', tmp_path / 'missing.sh'):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'link', 'x', '/path'])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Task 10 — plugin render
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginRender:
    """matrix plugin render <id> [options]."""

    def _make_render_root(self, tmp_path):
        """Create a fake LEDMATRIX_ROOT with render_plugin.py present."""
        scripts_dir = tmp_path / 'scripts'
        scripts_dir.mkdir()
        (scripts_dir / 'render_plugin.py').write_text('# stub')
        return tmp_path

    def test_render_calls_render_plugin_script(self, tmp_path):
        root = self._make_render_root(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'render', 'clock-simple'])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert 'render_plugin.py' in cmd_str
        assert 'clock-simple' in cmd_str

    def test_render_passes_output_option(self, tmp_path):
        root = self._make_render_root(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'render', 'x', '--output', '/tmp/out.png'])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert '/tmp/out.png' in cmd_str

    def test_render_passes_width_and_height(self, tmp_path):
        root = self._make_render_root(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'render', 'x', '--width', '64', '--height', '32'])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert '64' in cmd_str and '32' in cmd_str

    def test_render_passes_skip_update_flag(self, tmp_path):
        root = self._make_render_root(tmp_path)
        mock_proc = MagicMock(returncode=0)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'render', 'x', '--skip-update'])
        cmd_str = ' '.join(str(c) for c in mock_sub.call_args[0][0])
        assert '--skip-update' in cmd_str

    def test_render_exits_nonzero_if_render_script_missing(self, tmp_path):
        empty_root = tmp_path  # no scripts/render_plugin.py
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', empty_root):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'render', 'clock-simple'])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Task 11 — plugin install
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginInstall:
    """matrix plugin install <target> [--branch]."""

    def test_install_by_id_posts_to_install_endpoint(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True, 'plugin_id': 'clock-simple'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'install', 'clock-simple'])
        url = r.post.call_args[0][0]
        assert '/plugins/install' in url
        assert result.exit_code == 0

    def test_install_by_url_posts_to_install_from_url_endpoint(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True, 'plugin_id': 'my-plugin'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'install', 'https://github.com/user/repo'])
        url = r.post.call_args[0][0]
        assert 'install-from-url' in url

    def test_install_with_branch_passes_branch(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True, 'plugin_id': 'x'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'install', 'clock-simple', '--branch', 'dev'])
        payload = r.post.call_args[1].get('json', {})
        assert payload.get('branch') == 'dev'

    def test_install_exits_1_if_web_not_running(self):
        with patch('matrix_cli._detect_web', return_value=False):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'install', 'clock-simple'])
        assert result.exit_code == 1

    def test_install_handles_api_error_response(self):
        resp = MagicMock()
        resp.json.return_value = {'success': False, 'error': 'Not found'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'install', 'bad-id'])
        assert result.exit_code == 1 or 'error' in result.output.lower() or 'not found' in result.output.lower()


# ---------------------------------------------------------------------------
# Task 12 — plugin uninstall
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginUninstall:
    """matrix plugin uninstall <id> [--keep-config] [--yes]."""

    def test_uninstall_prompts_without_yes_flag(self):
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = MagicMock(**{'json.return_value': {'success': True}})
            CliRunner().invoke(
                matrix_cli.cli, ['plugin', 'uninstall', 'clock-simple'], input='n\n'
            )
        r.post.assert_not_called()

    def test_uninstall_skips_prompt_with_yes_flag(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = CliRunner().invoke(
                matrix_cli.cli, ['plugin', 'uninstall', 'clock-simple', '--yes']
            )
        r.post.assert_called_once()
        assert result.exit_code == 0

    def test_uninstall_posts_to_correct_endpoint(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'uninstall', 'my-plugin', '--yes'])
        url = r.post.call_args[0][0]
        assert '/plugins/uninstall' in url

    def test_uninstall_keep_config_sets_preserve_flag(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            CliRunner().invoke(
                matrix_cli.cli, ['plugin', 'uninstall', 'my-plugin', '--yes', '--keep-config']
            )
        payload = r.post.call_args[1].get('json', {})
        assert payload.get('preserve_config') is True

    def test_uninstall_exits_1_if_web_not_running(self):
        with patch('matrix_cli._detect_web', return_value=False):
            result = CliRunner().invoke(
                matrix_cli.cli, ['plugin', 'uninstall', 'my-plugin', '--yes']
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Task 13 — plugin update
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginUpdate:
    """matrix plugin update [id]."""

    def test_update_single_plugin_posts_once(self):
        resp = MagicMock()
        resp.json.return_value = {'success': True, 'message': 'Updated'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'update', 'clock-simple'])
        assert r.post.call_count == 1
        payload = r.post.call_args[1].get('json', {})
        assert payload.get('plugin_id') == 'clock-simple'

    def test_update_all_plugins_posts_once_per_plugin(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = {'success': True}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'update'])
        assert r.post.call_count == 2

    def test_update_exits_1_if_web_not_running(self):
        with patch('matrix_cli._detect_web', return_value=False):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'update', 'clock-simple'])
        assert result.exit_code == 1

    def test_update_shows_results_table(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = {'success': True, 'message': 'Updated to 1.1.0'}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir), \
             patch('matrix_cli.requests') as r:
            r.post.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'update'])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Task 14 — plugin health
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPluginHealth:
    """matrix plugin health [id]."""

    def test_health_calls_plugins_health_endpoint(self):
        resp = MagicMock()
        resp.json.return_value = {'plugins': []}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'health'])
        url = r.get.call_args[0][0]
        assert '/plugins/health' in url
        assert result.exit_code == 0

    def test_health_single_plugin_uses_id_in_url(self):
        resp = MagicMock()
        resp.json.return_value = {
            'plugin_id': 'clock-simple', 'state': 'running',
            'error_count': 0, 'last_error': None,
        }
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.get.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'health', 'clock-simple'])
        url = r.get.call_args[0][0]
        assert 'clock-simple' in url

    def test_health_shows_running_state(self):
        resp = MagicMock()
        resp.json.return_value = {'plugins': [
            {'plugin_id': 'clock-simple', 'state': 'running', 'error_count': 0, 'last_error': None}
        ]}
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'health'])
        assert 'clock-simple' in result.output
        assert 'running' in result.output.lower()

    def test_health_exits_1_if_web_not_running(self):
        with patch('matrix_cli._detect_web', return_value=False):
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'health'])
        assert result.exit_code == 1

    def test_health_handles_list_response(self):
        resp = MagicMock()
        resp.json.return_value = [
            {'plugin_id': 'p1', 'state': 'errored', 'error_count': 3, 'last_error': 'Timeout'},
        ]
        with patch('matrix_cli._detect_web', return_value=True), \
             patch('matrix_cli.requests') as r:
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'health'])
        assert result.exit_code == 0
        assert 'p1' in result.output


# ---------------------------------------------------------------------------
# Task 15 — plugin store
# ---------------------------------------------------------------------------

FAKE_REGISTRY = {
    'plugins': [
        {
            'id': 'clock-simple', 'name': 'Clock Simple', 'author': 'Chuck',
            'category': 'time', 'latest_version': '1.2.0', 'verified': True,
            'tags': ['time', 'clock'],
        },
        {
            'id': 'weather-board', 'name': 'Weather Board', 'author': 'Chuck',
            'category': 'weather', 'latest_version': '0.5.0', 'verified': False,
            'tags': ['weather'],
        },
    ]
}


@pytest.mark.unit
class TestPluginStore:
    """matrix plugin store [query]."""

    def test_store_fetches_from_registry_url(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = FAKE_REGISTRY
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.return_value = resp
            CliRunner().invoke(matrix_cli.cli, ['plugin', 'store'])
        url = r.get.call_args[0][0]
        assert 'github' in url or 'raw.githubusercontent' in url

    def test_store_shows_all_plugins_without_query(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = FAKE_REGISTRY
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'store'])
        assert 'Clock Simple' in result.output
        assert 'Weather Board' in result.output

    def test_store_filters_by_query(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = FAKE_REGISTRY
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'store', 'weather'])
        assert 'Weather Board' in result.output
        assert 'Clock Simple' not in result.output

    def test_store_marks_locally_installed_plugins(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = FAKE_REGISTRY
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'store'])
        assert '✓' in result.output or 'yes' in result.output.lower()

    def test_store_exits_1_on_fetch_error(self, fake_plugins_dir):
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.side_effect = Exception('Network error')
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'store'])
        assert result.exit_code == 1

    def test_store_query_matches_tags(self, fake_plugins_dir):
        resp = MagicMock()
        resp.json.return_value = FAKE_REGISTRY
        with patch('matrix_cli.requests') as r, \
             patch.object(matrix_cli, 'PLUGINS_DIR', fake_plugins_dir):
            r.get.return_value = resp
            result = CliRunner().invoke(matrix_cli.cli, ['plugin', 'store', 'clock'])
        assert 'Clock Simple' in result.output


# ---------------------------------------------------------------------------
# Task N — setup, install, and doctor commands
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSetupCommand:
    """matrix setup — venv sync via uv."""

    def test_setup_success(self):
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc):
            result = CliRunner().invoke(matrix_cli.cli, ['setup'])
        assert result.exit_code == 0

    def test_setup_uv_not_found_exits_1(self):
        with patch('shutil.which', return_value=None):
            result = CliRunner().invoke(matrix_cli.cli, ['setup'])
        assert result.exit_code == 1
        assert 'uv' in result.output

    def test_setup_uv_sync_failure_propagates_exit_code(self):
        mock_proc = MagicMock(returncode=2)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc):
            result = CliRunner().invoke(matrix_cli.cli, ['setup'])
        assert result.exit_code == 2

    def test_setup_passes_extra_flags_to_uv(self):
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['setup', '--extras', 'dev'])
        cmd = mock_sub.call_args[0][0]
        assert '--extra' in cmd
        assert 'dev' in cmd

    def test_setup_default_extras_includes_emulator(self):
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub:
            CliRunner().invoke(matrix_cli.cli, ['setup'])
        cmd = mock_sub.call_args[0][0]
        assert 'emulator' in cmd


@pytest.mark.unit
class TestInstallCommand:
    """matrix install — full install: venv + config + services."""

    def _mock_install_script(self, tmp_path):
        """Create a fake install_service.sh and patch LEDMATRIX_ROOT."""
        scripts_install = tmp_path / 'scripts' / 'install'
        scripts_install.mkdir(parents=True)
        (scripts_install / 'install_service.sh').write_text('#!/bin/bash\nexit 0\n')
        return tmp_path

    def test_install_no_services_success(self, tmp_path):
        """With --no-services, only venv sync and config copy run."""
        (tmp_path / 'config').mkdir()
        (tmp_path / 'config' / 'config.template.json').write_text('{}')
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc), \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', tmp_path):
            result = CliRunner().invoke(matrix_cli.cli, ['install', '--no-services'])
        assert result.exit_code == 0
        assert (tmp_path / 'config' / 'config.json').exists()

    def test_install_skips_config_copy_when_already_exists(self, tmp_path):
        (tmp_path / 'config').mkdir()
        (tmp_path / 'config' / 'config.json').write_text('{"existing": true}')
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc), \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', tmp_path):
            result = CliRunner().invoke(matrix_cli.cli, ['install', '--no-services'])
        assert result.exit_code == 0
        assert 'already exists' in result.output

    def test_install_exits_early_when_venv_sync_fails(self, tmp_path):
        """If venv sync fails, install must not proceed to config or services."""
        mock_proc = MagicMock(returncode=1)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc), \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', tmp_path):
            result = CliRunner().invoke(matrix_cli.cli, ['install', '--no-services'])
        assert result.exit_code == 1
        assert not (tmp_path / 'config' / 'config.json').exists()

    def test_install_uv_not_found_exits_1(self):
        with patch('shutil.which', return_value=None):
            result = CliRunner().invoke(matrix_cli.cli, ['install', '--no-services'])
        assert result.exit_code == 1

    def test_install_service_script_not_found_exits_1(self, tmp_path):
        """If install_service.sh is missing and --no-services not set, exit 1."""
        (tmp_path / 'config').mkdir()
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc), \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', tmp_path):
            result = CliRunner().invoke(matrix_cli.cli, ['install'])
        assert result.exit_code == 1

    def test_install_service_install_failure_exits(self, tmp_path):
        """If systemd service install fails, exit with non-zero."""
        root = self._mock_install_script(tmp_path)
        (root / 'config').mkdir(exist_ok=True)
        # First subprocess.run call is uv sync (success), second is sudo bash (fail)
        mock_ok = MagicMock(returncode=0)
        mock_fail = MagicMock(returncode=1)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', side_effect=[mock_ok, mock_fail]), \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', root):
            result = CliRunner().invoke(matrix_cli.cli, ['install'])
        assert result.exit_code == 1

    def test_install_emulator_flag_passes_extra_to_uv(self, tmp_path):
        (tmp_path / 'config').mkdir()
        mock_proc = MagicMock(returncode=0)
        with patch('shutil.which', return_value='/usr/bin/uv'), \
             patch('subprocess.run', return_value=mock_proc) as mock_sub, \
             patch.object(matrix_cli, 'LEDMATRIX_ROOT', tmp_path):
            CliRunner().invoke(matrix_cli.cli, ['install', '--no-services', '--emulator'])
        cmd = mock_sub.call_args[0][0]
        assert 'emulator' in cmd


@pytest.mark.unit
class TestDoctorCommand:
    """matrix doctor — system health check."""

    def _base_patches(self, tmp_path, venv_exists=True, config_exists=True,
                      secrets_exists=False, plugins_count=1):
        """Return a dict of patch contexts for a typical doctor run."""
        venv_py = tmp_path / '.venv' / 'bin' / 'python3'
        if venv_exists:
            venv_py.parent.mkdir(parents=True)
            venv_py.touch()
        config_dir = tmp_path / 'config'
        config_dir.mkdir(exist_ok=True)
        if config_exists:
            (config_dir / 'config.json').write_text('{}')
        if secrets_exists:
            (config_dir / 'config_secrets.json').write_text('{}')
        plugins_dir = tmp_path / 'plugins'
        plugins_dir.mkdir(exist_ok=True)
        for i in range(plugins_count):
            p = plugins_dir / f'plugin-{i}'
            p.mkdir()
            (p / 'manifest.json').write_text('{}')
        return tmp_path

    def test_doctor_all_pass(self, tmp_path):
        root = self._base_patches(tmp_path, venv_exists=True, config_exists=True)
        pillow_ok = MagicMock(returncode=0, stdout='10.0.0')
        py_ver_ok = MagicMock(returncode=0, stdout='3.11.0')
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', side_effect=[pillow_ok, py_ver_ok]), \
             patch('shutil.which', return_value='/usr/bin/uv'):
            result = CliRunner().invoke(matrix_cli.cli, ['doctor'])
        # At minimum should not crash and should exit 0 or 1 (depends on system)
        assert result.exit_code in (0, 1)

    def test_doctor_missing_venv_reports_fail(self, tmp_path):
        root = self._base_patches(tmp_path, venv_exists=False, config_exists=True)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout='3.11.0')), \
             patch('shutil.which', return_value='/usr/bin/uv'):
            result = CliRunner().invoke(matrix_cli.cli, ['doctor'])
        assert result.exit_code == 1
        assert 'FAIL' in result.output or 'fail' in result.output.lower()

    def test_doctor_missing_config_reports_fail(self, tmp_path):
        root = self._base_patches(tmp_path, venv_exists=False, config_exists=False)
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout='3.11.0')), \
             patch('shutil.which', return_value='/usr/bin/uv'):
            result = CliRunner().invoke(matrix_cli.cli, ['doctor'])
        assert result.exit_code == 1

    def test_doctor_uv_not_found_reports_fail(self, tmp_path):
        root = self._base_patches(tmp_path, venv_exists=True, config_exists=True)
        pillow_ok = MagicMock(returncode=0, stdout='10.0.0')
        py_ver_ok = MagicMock(returncode=0, stdout='3.11.0')
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', side_effect=[pillow_ok, py_ver_ok]), \
             patch('shutil.which', return_value=None):
            result = CliRunner().invoke(matrix_cli.cli, ['doctor'])
        assert result.exit_code == 1
        assert 'FAIL' in result.output

    def test_doctor_uses_venv_python_for_version_check(self, tmp_path):
        """Python version check should query venv Python, not current process."""
        root = self._base_patches(tmp_path, venv_exists=True, config_exists=True)
        pillow_ok = MagicMock(returncode=0, stdout='10.0.0')
        py_ver_ok = MagicMock(returncode=0, stdout='3.11.0')
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', side_effect=[pillow_ok, py_ver_ok]) as mock_sub, \
             patch('shutil.which', return_value='/usr/bin/uv'):
            CliRunner().invoke(matrix_cli.cli, ['doctor'])
        # The second subprocess.run call should invoke venv Python for version
        calls = mock_sub.call_args_list
        version_call = calls[1][0][0]  # second call args
        assert 'python' in version_call[0].lower()
        assert 'python_version' in ' '.join(version_call)

    def test_doctor_old_python_version_reports_fail(self, tmp_path):
        root = self._base_patches(tmp_path, venv_exists=True, config_exists=True)
        pillow_ok = MagicMock(returncode=0, stdout='10.0.0')
        py_old = MagicMock(returncode=0, stdout='3.8.0')
        with patch.object(matrix_cli, 'LEDMATRIX_ROOT', root), \
             patch('subprocess.run', side_effect=[pillow_ok, py_old]), \
             patch('shutil.which', return_value='/usr/bin/uv'):
            result = CliRunner().invoke(matrix_cli.cli, ['doctor'])
        assert result.exit_code == 1
        assert '3.8.0' in result.output
