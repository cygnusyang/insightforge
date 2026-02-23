"""告警模块

提供告警管理功能，包括告警创建、通知发送、告警解决等。

告警需求:
- FUNC-019 (实时监控和告警): 支持实时监控和告警
"""

from __future__ import annotations

import hashlib
import json
import hmac
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import httpx
from rich.console import Console

console = Console()


class AlertLevel(Enum):
    """告警级别"""
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警"""
    id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    rule: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def resolve(self):
        """解决告警"""
        self.resolved = True
        self.resolved_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "rule": self.rule,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class AlertConfig:
    """告警配置"""
    enable: bool = True
    failure_rate_threshold: float = 0.1  # 10%
    processing_time_threshold_seconds: float = 30.0
    cooldown_minutes: int = 5  # 告警冷却时间
    
    # 邮件配置
    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""
    to_addresses: List[str] = field(default_factory=list)
    
    # Webhook配置
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    
    def __post_init__(self):
        if self.to_addresses is None:
            self.to_addresses = []
        if self.smtp_port <= 0:
            self.smtp_port = 587
        if self.cooldown_minutes <= 0:
            self.cooldown_minutes = 5


class AlertReceiver:
    """告警接收者基类"""
    
    def send(self, alert: Alert) -> bool:
        """发送告警
        
        Args:
            alert: 告警对象
            
        Returns:
            bool: 发送是否成功
        """
        raise NotImplementedError


class EmailReceiver(AlertReceiver):
    """邮件接收者"""
    
    def __init__(self, smtp_config: Dict[str, str], to_addresses: List[str]):
        """
        Args:
            smtp_config: SMTP配置字典，包含 host, port, user, password, from_address
            to_addresses: 收件人地址列表
        """
        self.smtp_config = smtp_config
        self.to_addresses = to_addresses
    
    def send(self, alert: Alert) -> bool:
        """通过邮件发送告警
        
        Args:
            alert: 告警对象
            
        Returns:
            bool: 发送是否成功
        """
        if not self.to_addresses:
            console.print(f"[yellow]警告: 邮件接收者列表为空，跳过发送[/yellow]")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # 构建邮件内容
            subject = f"[{alert.level.value.upper()}] 告警: {alert.message[:50]}..."
            body = f"""
告警详情:
- 级别: {alert.level.value.upper()}
- 消息: {alert.message}
- 规则: {alert.rule}
- 时间: {alert.timestamp.isoformat()}
- ID: {alert.id}
"""
            
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config.get("from_address", "")
            msg["To"] = ", ".join(self.to_addresses)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # 发送邮件
            host = self.smtp_config.get("host", "")
            port = int(self.smtp_config.get("port", 587))
            user = self.smtp_config.get("user", "")
            password = self.smtp_config.get("password", "")
            
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(msg["From"], self.to_addresses, msg.as_string())
            
            console.print(f"[green]✓ 邮件告警发送成功: {', '.join(self.to_addresses)}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ 邮件告警发送失败: {e}[/red]")
            return False


class WebhookReceiver(AlertReceiver):
    """Webhook接收者"""
    
    def __init__(self, url: str, secret: Optional[str] = None, method: str = "POST"):
        """
        Args:
            url: Webhook URL
            secret: 密钥，用于签名验证
            method: HTTP方法，默认POST
        """
        self.url = url
        self.secret = secret
        self.method = method.upper()
    
    def send(self, alert: Alert) -> bool:
        """通过Webhook发送告警
        
        Args:
            alert: 告警对象
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建消息内容
            message = {
                "alert_id": alert.id,
                "level": alert.level.value,
                "message": alert.message,
                "rule": alert.rule,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
            }
            
            # 如果有密钥，添加签名
            headers = {"Content-Type": "application/json"}
            if self.secret:
                payload_str = json.dumps(message, separators=(",", ":"))
                signature = hmac.new(
                    self.secret.encode(), payload_str.encode(), hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = signature
            
            # 发送请求
            with httpx.Client() as client:
                response = client.request(
                    method=self.method,
                    url=self.url,
                    json=message,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()
            
            console.print(f"[green]✓ Webhook告警发送成功: {self.url}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Webhook告警发送失败: {e}[/red]")
            return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Args:
            config: 告警配置
        """
        self.config = config or AlertConfig()
        self.alerts: List[Alert] = []
        self.receivers: List[AlertReceiver] = []
        self._last_alert_time: Dict[str, datetime] = {}
        
        # 初始化接收者
        self._init_receivers()
    
    def _init_receivers(self):
        """初始化告警接收者"""
        # 邮件接收者
        if self.config.email_enabled:
            smtp_config = {
                "host": self.config.smtp_host,
                "port": str(self.config.smtp_port),
                "user": self.config.smtp_user,
                "password": self.config.smtp_password,
                "from_address": self.config.from_address,
            }
            if smtp_config["host"] and smtp_config["from_address"]:
                self.receivers.append(EmailReceiver(smtp_config, self.config.to_addresses))
        
        # Webhook接收者
        if self.config.webhook_enabled:
            if self.config.webhook_url:
                self.receivers.append(
                    WebhookReceiver(
                        url=self.config.webhook_url,
                        secret=self.config.webhook_secret or None,
                    )
                )
    
    def create_alert(self, level: AlertLevel, message: str, rule: str) -> Optional[Alert]:
        """创建告警
        
        Args:
            level: 告警级别
            message: 告警消息
            rule: 触发规则
            
        Returns:
            Alert: 创建的告警对象，如果被抑制则返回None
        """
        if not self.config.enable:
            return None
        
        # 生成告警ID
        alert_id = self._generate_alert_id(level, message, rule)
        
        # 检查冷却时间
        if alert_id in self._last_alert_time:
            elapsed = (datetime.now() - self._last_alert_time[alert_id]).total_seconds()
            if elapsed < self.config.cooldown_minutes * 60:
                console.print(f"[yellow]告警 {alert_id} 处于冷却期，跳过发送[/yellow]")
                return None
        
        # 创建告警
        alert = Alert(
            id=alert_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
            rule=rule,
        )
        
        self.alerts.append(alert)
        self._last_alert_time[alert_id] = datetime.now()
        
        # 发送通知
        self._notify(alert)
        
        return alert
    
    def _generate_alert_id(self, level: AlertLevel, message: str, rule: str) -> str:
        """生成告警ID"""
        content = f"{level.value}:{message}:{rule}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _notify(self, alert: Alert):
        """发送告警通知
        
        Args:
            alert: 告警对象
        """
        for receiver in self.receivers:
            receiver.send(alert)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警
        
        Args:
            alert_id: 告警ID
            
        Returns:
            bool: 是否成功解决
        """
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolve()
                console.print(f"[green]告警 {alert_id} 已解决[/green]")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警
        
        Returns:
            List[Alert]: 活跃告警列表
        """
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """按级别获取告警
        
        Args:
            level: 告警级别
            
        Returns:
            List[Alert]: 告警列表
        """
        return [alert for alert in self.alerts if alert.level == level]
    
    def clear_resolved_alerts(self):
        """清除已解决的告警"""
        self.alerts = [alert for alert in self.alerts if not alert.resolved]
