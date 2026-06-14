from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexura.models.schemas import ScanResult, ToolCommand, ToolType


class TestScanRunner:
    @patch("nexura.runner.shutil.which")
    def test_run_tool_not_found(self, mock_which):
        from nexura.runner import ScanRunner
        mock_which.return_value = None
        runner = ScanRunner()
        cmd = ToolCommand(tool=ToolType.NMAP, args=["example.com"], description="")
        with patch("nexura.runner.TOOL_PATHS", {}):
            result = runner.run(cmd, "example.com")
            assert not result.success
            assert "topilmadi" in result.error


    @patch("os.path.isfile")
    @patch("nexura.runner.ScanRunner._execute")
    def test_run_success(self, mock_exec, mock_isfile):
        from nexura.runner import ScanRunner
        mock_isfile.return_value = True
        mock_exec.return_value = ("Nmap done: 1 IP address", 0)
        runner = ScanRunner()
        cmd = ToolCommand(tool=ToolType.NMAP, args=["example.com"], description="")
        result = runner.run(cmd, "example.com")
        assert result.success
        assert result.tool == "nmap"


    @patch("os.path.isfile")
    @patch("nexura.runner.ScanRunner._execute")
    def test_run_failure_exit_code(self, mock_exec, mock_isfile):
        from nexura.runner import ScanRunner
        mock_isfile.return_value = True
        mock_exec.return_value = ("Error: invalid target", 1)
        runner = ScanRunner()
        cmd = ToolCommand(tool=ToolType.NMAP, args=["bad-target"], description="")
        result = runner.run(cmd, "bad-target")
        assert not result.success


    def test_network_tool(self):
        from nexura.runner import ScanRunner
        runner = ScanRunner()
        cmd = ToolCommand(tool=ToolType.NETWORK, args=["80"], description="")
        with patch("nexura.runner.NetworkScanner") as mock_scanner:
            mock_instance = mock_scanner.return_value
            mock_instance.quick_scan.return_value = ScanResult(
                tool="network", target="localhost", start_time=datetime.now(), success=True
            )
            runner.run(cmd, "localhost")
            mock_scanner.return_value.quick_scan.assert_called_once()


    def test_execute_timeout(self):
        from nexura.runner import ScanRunner
        runner = ScanRunner()
        with patch("nexura.runner.subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=1)
            output, code = runner._execute(["sleep", "10"])
            assert code == -1
            assert "TIMEOUT" in output


class TestToolSelector:
    def test_validate_target(self):
        from nexura.ai_engine import AIEngine
        from nexura.tool_selector import ToolSelector
        selector = ToolSelector(AIEngine())
        assert selector._validate_target("example.com")
        assert selector._validate_target("192.168.1.1")
        assert selector._validate_target("http://example.com/path")
        assert not selector._validate_target("")
        assert not selector._validate_target("invalid space")
        assert not selector._validate_target("unknown")


    def test_fallback_plan(self):
        from nexura.ai_engine import AIEngine
        from nexura.tool_selector import ToolSelector
        selector = ToolSelector(AIEngine())
        plan = selector._fallback_plan("test scan", "example.com", "AI not available")
        assert len(plan.tools) == 2
        assert plan.tools[0].tool == ToolType.NMAP


class TestHistoryDB:
    def test_init_db(self):
        with patch("nexura.history_db._init_db") as mock_init:
            from nexura.history_db import HistoryDB
            HistoryDB()
            mock_init.assert_called_once()


    def test_get_stats_empty(self):
        with patch("nexura.history_db._init_db"):
            from nexura.history_db import HistoryDB
            db = HistoryDB()
            with patch.object(db, "_get_conn") as mock_conn:
                mock_cursor = MagicMock()
                mock_cursor.fetchone.return_value = {"cnt": 0}
                mock_conn.return_value.execute.return_value = mock_cursor
                stats = db.get_stats()
                assert stats["total_scans"] == 0
                assert stats["total_vulns"] == 0


class TestExtractJson:

    def _extract(self, text: str) -> dict:
        from nexura.ai_engine import extract_json
        return extract_json(text)

    def test_valid_json(self):
        result = self._extract('{"target": "example.com", "tools": []}')
        assert result["target"] == "example.com"

    def test_markdown_fence(self):
        result = self._extract('```json\n{"target": "example.com"}\n```')
        assert result["target"] == "example.com"

    def test_markdown_fence_no_lang(self):
        result = self._extract('```\n{"target": "example.com"}\n```')
        assert result["target"] == "example.com"

    def test_uzbek_apostrophe(self):
        text = '{"reasoning": "to\'liq tahlil kerak", "target": "example.com"}'
        result = self._extract(text)
        assert result["reasoning"] == "to'liq tahlil kerak"

    def test_uzbek_apostrophe_with_single_quotes(self):
        text = "{'reasoning': 'to\'liq tahlil', 'target': 'example.com'}"
        result = self._extract(text)
        assert result["reasoning"] == "to'liq tahlil"
        assert result["target"] == "example.com"

    def test_trailing_comma_object(self):
        result = self._extract('{"a": 1, "b": 2,}')
        assert result["a"] == 1
        assert result["b"] == 2

    def test_trailing_comma_array(self):
        result = self._extract('{"tools": ["nmap", "nuclei",]}')
        assert result["tools"] == ["nmap", "nuclei"]

    def test_extra_text_before_after(self):
        result = self._extract('Mana natija: {"target": "example.com"} Tugadi.')
        assert result["target"] == "example.com"

    def test_extra_text_with_reasoning(self):
        result = self._extract('AI javobi:\n{"target": "example.com"}\n\nYuqoridagi skaner rejasi.')
        assert result["target"] == "example.com"

    def test_unquoted_keys(self):
        result = self._extract('{target: "example.com", intent: "test"}')
        assert result["target"] == "example.com"
        assert result["intent"] == "test"

    def test_unquoted_keys_nested(self):
        result = self._extract('{target: "example.com", nested: {inner: true}}')
        assert result["target"] == "example.com"
        assert result["nested"]["inner"] is True

    def test_mixed_issues(self):
        text = (
            '```json\n'
            "{'target': 'example.com', 'intent': 'to'liq audit', 'tools': [{'tool': 'nmap', 'args': ['-sV', '<target>'], 'description': 'Port skaner'},], 'agentic': true}\n"
            '```'
        )
        result = self._extract(text)
        assert result["target"] == "example.com"
        assert result["intent"] == "to'liq audit"
        assert result["agentic"] is True
        assert len(result["tools"]) == 1
        assert result["tools"][0]["tool"] == "nmap"

    def test_single_quoted_keys(self):
        result = self._extract("{'target': 'example.com', 'intent': 'quick scan'}")
        assert result["target"] == "example.com"
        assert result["intent"] == "quick scan"

    def test_single_quotes_with_colon_in_value(self):
        result = self._extract("{'target': 'http://example.com:8080'}")
        assert result["target"] == "http://example.com:8080"

    def test_already_valid_json_unchanged(self):
        text = '{"target": "example.com", "data": {"nested": true}}'
        result = self._extract(text)
        assert result == {"target": "example.com", "data": {"nested": True}}

    def test_invalid_json_raises(self):
        from nexura.ai_engine import extract_json
        import pytest
        with pytest.raises(ValueError, match="Model JSON qaytarmadi"):
            extract_json("bu umuman JSON emas")

    def test_both_trailing_commas(self):
        result = self._extract('{"a": [1, 2,], "b": {"c": 3,}}')
        assert result["a"] == [1, 2]
        assert result["b"]["c"] == 3


class TestCVELookup:
    @pytest.mark.asyncio
    async def test_lookup_empty_service(self):
        from nexura.cve_lookup import CVELookup
        cve = CVELookup()
        result = await cve.lookup_by_service("", "")
        assert result == []


    @pytest.mark.asyncio
    async def test_lookup_by_cve_not_found(self):
        from nexura.cve_lookup import CVELookup
        cve = CVELookup()
        with patch.object(cve, "_async_client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_response)
            result = await cve.lookup_by_cve("CVE-9999-99999")
            assert result is None
