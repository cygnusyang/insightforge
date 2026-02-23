"""告警模块单元测试

测试告警模块的功能，包括告警创建、通知发送、告警解决等。

测试需求:
- FUNC-019 (实时监控和告警): 支持实时监控和告警
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.opportunity_detector.alert import (
    Alert,
    AlertConfig,
    AlertLevel,
    AlertManager,
    EmailReceiver,
    WebhookReceiver,
)


class TestAlert:
    """测试告警"""
    
    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            id="test_alert",
            level=AlertLevel.WARNING,
            message="Test alert message",
            timestamp=datetime.now(),
            rule="test_rule",
        )
        
        assert alert.id == "test_alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test alert message"
        assert alert.rule == "test_rule"
        assert not alert.resolved
    
    def test_alert_resolve(self):
        """测试告警解决"""
        alert = Alert(
            id="test_alert",
            level=AlertLevel.WARNING,
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
            level=AlertLevel.WARNING,
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


class TestAlertConfig:
    """测试告警配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AlertConfig()
        
        assert config.enable
        assert config.failure_rate_threshold == 0.1
        assert config.processing_time_threshold_seconds == 30.0
        assert config.cooldown_minutes == 5
        assert not config.email_enabled
        assert not config.webhook_enabled
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AlertConfig(
            enable=True,
            failure_rate_threshold=0.2,
            processing_time_threshold_seconds=60.0,
            cooldown_minutes=10,
            email_enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            from_address="from@example.com",
            to_addresses=["to@example.com"],
            webhook_enabled=True,
            webhook_url="https://example.com/webhook",
            webhook_secret="secret",
        )
        
        assert config.enable
        assert config.failure_rate_threshold == 0.2
        assert config.processing_time_threshold_seconds == 60.0
        assert config.cooldown_minutes == 10
        assert config.email_enabled
        assert config.smtp_host == "smtp.example.com"
        assert config.webhook_enabled
        assert config.webhook_url == "https://example.com/webhook"


class TestAlertManager:
    """测试告警管理器"""
    
    def test_create_alert(self):
        """测试创建告警"""
        config = AlertConfig(enable=True)
        manager = AlertManager(config)
        
        alert = manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test alert",
            rule="test_rule",
        )
        
        assert alert is not None
        assert alert.message == "Test alert"
        assert len(manager.alerts) == 1
    
    def test_create_alert_disabled(self):
        """测试创建告警（已禁用）"""
        config = AlertConfig(enable=False)
        manager = AlertManager(config)
        
        alert = manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test alert",
            rule="test_rule",
        )
        
        assert alert is None
        assert len(manager.alerts) == 0
    
    def test_resolve_alert(self):
        """测试解决告警"""
        config = AlertConfig(enable=True)
        manager = AlertManager(config)
        
        alert = manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test alert",
            rule="test_rule",
        )
        
        assert manager.resolve_alert(alert.id)
        assert alert.resolved
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        config = AlertConfig(enable=True)
        manager = AlertManager(config)
        
        alert1 = manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test alert 1",
            rule="test_rule",
        )
        alert2 = manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test alert 2",
            rule="test_rule",
        )
        
        manager.resolve_alert(alert1.id)
        
        active_alerts = manager.get_active_alerts()
        
        assert len(active_alerts) == 1
        assert active_alerts[0].id == alert2.id
    
    def test_get_alerts_by_level(self):
        """测试按级别获取告警"""
        config = AlertConfig(enable=True)
        manager = AlertManager(config)
        
        manager.create_alert(
            level=AlertLevel.WARNING,
            message="Test warning",
            rule="test_rule",
        )
        manager.create_alert(
            level=AlertLevel.CRITICAL,
            message="Test critical",
            rule="test_rule",
        )
        
        warnings = manager.get_alerts_by_level(AlertLevel.WARNING)
        criticals = manager.get_alerts_by_level(AlertLevel.CRITICAL)
        
        assert len(warnings) == 1
        assert len(criticals) == 1


class TestEmailReceiver:
    """测试邮件接收者"""
    
    def test_email_receiver_creation(self):
        """测试邮件接收者创建"""
        config = {
            "host": "smtp.example.com",
            "port": "587",
            "user": "user",
            "password": "password",
            "from_address": "from@example.com",
        }
        receiver = EmailReceiver(config, ["to@example.com"])
        
        assert receiver.smtp_config["host"] == "smtp.example.com"
        assert receiver.to_addresses == ["to@example.com"]
    
    def test_email_receiver_send(self):
        """测试邮件接收者发送（模拟）"""
        config = {
            "host": "smtp.example.com",
            "port": "587",
            "user": "user",
            "password": "password",
            "from_address": "from@example.com",
        }
        receiver = EmailReceiver(config, ["to@example.com"])
        
        alert = Alert(
            id="test_alert",
            level=AlertLevel.WARNING,
            message="Test alert",
            timestamp=datetime.now(),
            rule="test_rule",
        )
        
        # 注意：这里不实际发送邮件，只测试方法调用
        result = receiver.send(alert)
        # 由于没有真实的SMTP服务器，这里期望返回False
        assert not result


class TestWebhookReceiver:
    """测试Webhook接收者"""
    
    def test_webhook_receiver_creation(self):
        """测试Webhook接收者创建"""
        receiver = WebhookReceiver(
            url="https://example.com/webhook",
            secret="secret",
        )
        
        assert receiver.url == "https://example.com/webhook"
        assert receiver.secret == "secret"
    
    def test_webhook_receiver_send(self):
        """测试Webhook接收者发送（模拟）"""
        receiver = WebhookReceiver(
            url="https://example.com/webhook",
            secret="secret",
        )
        
        alert = Alert(
            id="test_alert",
            level=AlertLevel.WARNING,
            message="Test alert",
            timestamp=datetime.now(),
            rule="test_rule",
        )
        
        # 注意：这里不实际发送请求，只测试方法调用
        result = receiver.send(alert)
        # 由于没有真实的Webhook服务器，这里期望返回False
        assert not result
