"""监控模块单元测试

测试监控模块的功能，包括指标收集、告警规则检查等。

测试需求:
- FUNC-019 (实时监控和告警): 支持实时监控和告警
"""

from __future__ import annotations

import time
from datetime import datetime

import pytest

from src.opportunity_detector.monitor import Monitor, MonitorMetric, MonitorResult, Alert


class TestMonitorMetric:
    """测试监控指标"""
    
    def test_metric_creation(self):
        """测试指标创建"""
        metric = MonitorMetric(
            timestamp=datetime.now(),
            name="test_metric",
            value=1.0,
            labels={"source": "test"},
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 1.0
        assert metric.labels == {"source": "test"}
    
    def test_metric_to_dict(self):
        """测试指标转换为字典"""
        metric = MonitorMetric(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            name="test_metric",
            value=1.0,
            labels={"source": "test"},
        )
        
        result = metric.to_dict()
        
        assert result["name"] == "test_metric"
        assert result["value"] == 1.0
        assert result["labels"] == {"source": "test"}
        assert "timestamp" in result


class TestMonitor:
    """测试监控器"""
    
    def test_start_stop(self):
        """测试开始和停止监控"""
        monitor = Monitor()
        
        monitor.start()
        time.sleep(0.1)
        elapsed = monitor.stop()
        
        assert elapsed >= 0.1
    
    def test_record_data_collection_success(self):
        """测试记录数据采集成功"""
        monitor = Monitor()
        
        monitor.record_data_collection("gdelt", success=True, count=10)
        
        assert "gdelt" in monitor._collection_stats
        assert monitor._collection_stats["gdelt"]["success"] == 10
    
    def test_record_data_collection_failed(self):
        """测试记录数据采集失败"""
        monitor = Monitor()
        
        monitor.record_data_collection("gdelt", success=False, count=1)
        
        assert "gdelt" in monitor._collection_stats
        assert monitor._collection_stats["gdelt"]["failed"] == 1
    
    def test_record_api_call(self):
        """测试记录API调用"""
        monitor = Monitor()
        
        monitor.record_api_call("gdelt_api", success=True, duration=0.5)
        
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].name == "api_call_gdelt_api_duration"
        assert monitor.metrics[0].value == 0.5
    
    def test_record_processing_time(self):
        """测试记录处理时间"""
        monitor = Monitor()
        
        monitor.record_processing_time("data_collection", 5.0)
        
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].name == "processing_time_data_collection"
        assert monitor.metrics[0].value == 5.0
    
    def test_check_alert_rules_failure_rate(self):
        """测试告警规则 - 失败率"""
        monitor = Monitor(failure_rate_threshold=0.1)
        
        # 记录10次采集，其中2次失败（失败率20% > 10%）
        for _ in range(8):
            monitor.record_data_collection("gdelt", success=True)
        for _ in range(2):
            monitor.record_data_collection("gdelt", success=False)
        
        alerts = monitor.check_alert_rules()
        
        assert len(alerts) == 1
        assert "失败率" in alerts[0].message or "failure" in alerts[0].message.lower()
    
    def test_check_alert_rules_processing_time(self):
        """测试告警规则 - 处理时间"""
        monitor = Monitor(processing_time_threshold=10.0)
        
        # 记录处理时间超过阈值
        monitor.record_processing_time("data_collection", 15.0)
        
        alerts = monitor.check_alert_rules()
        
        assert len(alerts) == 1
        assert "processing" in alerts[0].message.lower() or "耗时" in alerts[0].message
    
    def test_get_summary(self):
        """测试获取监控摘要"""
        monitor = Monitor()
        
        monitor.record_data_collection("gdelt", success=True, count=10)
        monitor.record_data_collection("gdelt", success=False, count=1)
        monitor.record_processing_time("test", 5.0)
        
        summary = monitor.get_summary()
        
        assert "is_healthy" in summary
        assert "metrics_count" in summary
        assert "alerts_count" in summary
        assert "source_success_rates" in summary
        assert "gdelt" in summary["source_success_rates"]


class TestAlert:
    """测试告警"""
    
    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            id="test_alert",
            level="warning",
            message="Test alert message",
            timestamp=datetime.now(),
            rule="test_rule",
        )
        
        assert alert.id == "test_alert"
        assert alert.level == "warning"
        assert alert.message == "Test alert message"
        assert alert.rule == "test_rule"
        assert not alert.resolved
    
    def test_alert_resolve(self):
        """测试告警解决"""
        alert = Alert(
            id="test_alert",
            level="warning",
            message="Test alert message",
            timestamp=datetime.now(),
            rule="test_rule",
        )
        
        alert.resolve()
        
        assert alert.resolved
        assert alert.resolved_at is not None
    
    def test_alert_to_dict(self):
        """测试告警转换为字典"""
        alert = Alert(
            id="test_alert",
            level="warning",
            message="Test alert message",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            rule="test_rule",
        )
        
        result = alert.to_dict()
        
        assert result["id"] == "test_alert"
        assert result["level"] == "warning"
        assert result["message"] == "Test alert message"
        assert result["rule"] == "test_rule"
        assert not result["resolved"]
