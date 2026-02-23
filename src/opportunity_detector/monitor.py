"""监控模块

提供实时监控功能，包括数据采集成功率、API调用频率、处理延迟等指标的收集和检查。

监控需求:
- FUNC-019 (实时监控和告警): 支持实时监控和告警
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional



@dataclass
class MonitorMetric:
    """监控指标"""
    timestamp: datetime
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
        }


@dataclass
class Alert:
    """告警"""
    id: str
    level: str  # "warning" or "critical"
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
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "rule": self.rule,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class MonitorResult:
    """监控结果"""
    is_healthy: bool
    metrics: List[MonitorMetric]
    alerts: List[Alert]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "is_healthy": self.is_healthy,
            "metrics": [m.to_dict() for m in self.metrics],
            "alerts": [a.to_dict() for a in self.alerts],
        }


class Monitor:
    """监控器"""
    
    def __init__(self, failure_rate_threshold: float = 0.1, processing_time_threshold: float = 30.0):
        """
        Args:
            failure_rate_threshold: 失败率阈值，默认10%
            processing_time_threshold: 处理时间阈值（秒），默认30秒
        """
        self.metrics: List[MonitorMetric] = []
        self.alerts: List[Alert] = []
        self.failure_rate_threshold = failure_rate_threshold
        self.processing_time_threshold = processing_time_threshold
        self._start_time: Optional[float] = None
        self._data_points: Dict[str, List[float]] = {}
        self._collection_stats: Dict[str, Dict[str, int]] = {}

    def start(self):
        """开始监控"""
        self._start_time = time.time()

    def stop(self) -> float:
        """停止监控并返回总耗时"""
        if self._start_time is None:
            return 0.0
        elapsed = time.time() - self._start_time
        self._start_time = None
        return elapsed

    def record_data_collection(self, source: str, success: bool, count: int = 1):
        """记录数据采集结果
        
        Args:
            source: 数据源名称
            success: 是否成功
            count: 采集数量
        """
        if source not in self._collection_stats:
            self._collection_stats[source] = {"success": 0, "failed": 0}
        
        if success:
            self._collection_stats[source]["success"] += count
        else:
            self._collection_stats[source]["failed"] += count
        
        # 记录指标
        self.metrics.append(MonitorMetric(
            timestamp=datetime.now(),
            name=f"data_collection_{source}_success",
            value=1.0 if success else 0.0,
            labels={"source": source},
        ))

    def record_api_call(self, api: str, success: bool, duration: float):
        """记录API调用结果
        
        Args:
            api: API名称
            success: 是否成功
            duration: 调用耗时（秒）
        """
        # 记录指标
        self.metrics.append(MonitorMetric(
            timestamp=datetime.now(),
            name=f"api_call_{api}_duration",
            value=duration,
            labels={"api": api, "success": str(success).lower()},
        ))

    def record_processing_time(self, stage: str, duration: float):
        """记录处理时间
        
        Args:
            stage: 处理阶段名称
            duration: 处理耗时（秒）
        """
        self.metrics.append(MonitorMetric(
            timestamp=datetime.now(),
            name=f"processing_time_{stage}",
            value=duration,
            labels={"stage": stage},
        ))

    def check_alert_rules(self) -> List[Alert]:
        """检查告警规则
        
        Returns:
            List[Alert]: 触发的告警列表
        """
        triggered_alerts = []
        
        # 检查数据采集失败率
        for source, stats in self._collection_stats.items():
            total = stats["success"] + stats["failed"]
            if total > 0:
                failure_rate = stats["failed"] / total
                if failure_rate > self.failure_rate_threshold:
                    alert = Alert(
                        id=f"collection_failure_{source}",
                        level="warning",
                        message=f"数据源 {source} 采集失败率超过 {self.failure_rate_threshold*100:.0f}%: {failure_rate*100:.1f}%",
                        timestamp=datetime.now(),
                        rule="failure_rate_threshold",
                    )
                    triggered_alerts.append(alert)
        
        # 检查处理时间
        for metric in self.metrics:
            if metric.name.startswith("processing_time_"):
                if metric.value > self.processing_time_threshold:
                    alert = Alert(
                        id=f"processing_time_{metric.labels.get('stage', 'unknown')}",
                        level="warning",
                        message=f"处理阶段 {metric.labels.get('stage', 'unknown')} 耗时超过 {self.processing_time_threshold}秒: {metric.value:.1f}秒",
                        timestamp=datetime.now(),
                        rule="processing_time_threshold",
                    )
                    triggered_alerts.append(alert)
        
        # 更新告警列表
        self.alerts.extend(triggered_alerts)
        return triggered_alerts

    def get_status(self) -> MonitorResult:
        """获取监控状态
        
        Returns:
            MonitorResult: 监控状态
        """
        # 检查告警规则
        self.check_alert_rules()
        
        # 判断是否健康
        is_healthy = all(not alert.level == "critical" for alert in self.alerts)
        
        return MonitorResult(
            is_healthy=is_healthy,
            metrics=self.metrics,
            alerts=self.alerts,
        )

    def get_summary(self) -> dict:
        """获取监控摘要
        
        Returns:
            dict: 监控摘要
        """
        result = self.get_status()
        
        # 计算数据源成功率
        source_success_rates = {}
        for source, stats in self._collection_stats.items():
            total = stats["success"] + stats["failed"]
            if total > 0:
                success_rate = stats["success"] / total
                source_success_rates[source] = {
                    "success": stats["success"],
                    "failed": stats["failed"],
                    "success_rate": success_rate,
                }
        
        return {
            "is_healthy": result.is_healthy,
            "metrics_count": len(result.metrics),
            "alerts_count": len(result.alerts),
            "source_success_rates": source_success_rates,
        }
