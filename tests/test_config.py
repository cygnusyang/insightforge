"""配置验证测试模块

测试 DEV-001: 配置验证增强
"""

import pytest

from src.opportunity_detector.config import (
    DetectorConfig,
    Weights,
    load_config,
)


class TestWeightsValidation:
    """Weights 类的验证测试"""

    def test_weights_sum_valid(self) -> None:
        """测试权重之和为 1.0 的有效情况"""
        weights = Weights(demand=0.45, momentum=0.35, competition=0.20)
        assert abs(weights.demand + weights.momentum + weights.competition - 1.0) < 0.001

    def test_weights_sum_invalid(self) -> None:
        """测试权重之和不为 1.0 的情况"""
        # 使用 0.4 + 0.4 + 0.3 = 1.1，超过 1.0
        with pytest.raises(ValueError) as exc_info:
            Weights(demand=0.4, momentum=0.4, competition=0.3)
        error_msg = str(exc_info.value)
        assert "权重验证失败" in error_msg
        assert "demand" in error_msg
        assert "momentum" in error_msg
        assert "competition" in error_msg

    def test_weights_negative_value(self) -> None:
        """测试权重为负数的情况"""
        with pytest.raises(ValueError) as exc_info:
            Weights(demand=0.5, momentum=0.5, competition=-0.1)
        error_msg = str(exc_info.value)
        assert "权重验证失败" in error_msg
        assert "competition" in error_msg

    def test_weights_default_values(self) -> None:
        """测试权重的默认值"""
        weights = Weights()
        assert weights.demand == 0.45
        assert weights.momentum == 0.35
        assert weights.competition == 0.20
        assert abs(weights.demand + weights.momentum + weights.competition - 1.0) < 0.001


class TestDetectorConfigValidation:
    """DetectorConfig 类的验证测试"""

    def test_config_valid_basic(self) -> None:
        """测试基本的有效配置"""
        config = DetectorConfig(
            topics=["ai"],
            topic_keywords={"ai": ["artificial intelligence", "machine learning"]},
        )
        assert config.topics == ["ai"]
        assert config.topic_keywords == {"ai": ["artificial intelligence", "machine learning"]}

    def test_config_topics_empty(self) -> None:
        """测试 topics 为空的情况"""
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(
                topics=[],
                topic_keywords={},
            )
        error_msg = str(exc_info.value)
        assert "配置验证失败" in error_msg
        assert "topics" in error_msg

    def test_config_topics_missing_keywords(self) -> None:
        """测试 topics 缺少对应 topic_keywords 的情况"""
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(
                topics=["ai", "robotics"],
                topic_keywords={"ai": ["artificial intelligence"]},
                # robotics 缺少关键词
            )
        error_msg = str(exc_info.value)
        assert "配置验证失败" in error_msg
        assert "topic_keywords" in error_msg
        assert "robotics" in error_msg

    def test_config_recent_days_equal_to_window_days(self) -> None:
        """测试 recent_days 等于 window_days 的情况（应该失败）"""
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(
                window_days=30,
                recent_days=30,  # 等于 window_days，应该失败
                topics=["ai"],
                topic_keywords={"ai": ["test"]},
            )
        error_msg = str(exc_info.value)
        assert "时间窗口验证失败" in error_msg
        assert "recent_days" in error_msg
        assert "window_days" in error_msg

    def test_config_recent_days_greater_than_window_days(self) -> None:
        """测试 recent_days 大于 window_days 的情况"""
        # 使用 window_days=35 以避免 recent_days 的 Field 限制(le=30)
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(
                window_days=35,
                recent_days=36,  # 大于 window_days
                topics=["ai"],
                topic_keywords={"ai": ["test"]},
            )
        error_msg = str(exc_info.value)
        assert "时间窗口验证失败" in error_msg
        assert "recent_days" in error_msg
        assert "window_days" in error_msg

    def test_config_daily_days_equal_to_recent_days(self) -> None:
        """测试 daily_days 等于 recent_days 的情况（边界情况，应该通过）"""
        config = DetectorConfig(
            window_days=30,
            recent_days=7,
            daily_days=7,  # 等于 recent_days，边界情况，应该通过
            topics=["ai"],
            topic_keywords={"ai": ["test"]},
        )
        assert config.daily_days == config.recent_days

    def test_config_daily_days_greater_than_recent_days(self) -> None:
        """测试 daily_days 大于 recent_days 的情况"""
        # 使用 recent_days=6 以避免 daily_days 的 Field 限制(le=7)
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(
                window_days=30,
                recent_days=6,
                daily_days=7,  # 大于 recent_days
                topics=["ai"],
                topic_keywords={"ai": ["test"]},
            )
        error_msg = str(exc_info.value)
        assert "时间窗口验证失败" in error_msg
        assert "daily_days" in error_msg
        assert "recent_days" in error_msg

    def test_config_default_values(self) -> None:
        """测试配置的默认值"""
        config = DetectorConfig(
            topics=["ai"],
            topic_keywords={"ai": ["test"]},
        )
        assert config.window_days == 30
        assert config.recent_days == 7
        assert config.daily_days == 1
        assert config.weights.demand == 0.45
        assert config.weights.momentum == 0.35
        assert config.weights.competition == 0.20

    def test_config_time_windows_valid(self) -> None:
        """测试有效的时间窗口配置"""
        config = DetectorConfig(
            window_days=30,
            recent_days=7,
            daily_days=1,
            topics=["ai"],
            topic_keywords={"ai": ["test"]},
        )
        assert config.window_days > config.recent_days
        assert config.recent_days >= config.daily_days

    def test_config_time_windows_boundary(self) -> None:
        """测试时间窗口的边界情况"""
        # recent_days = window_days - 1 (有效)
        config = DetectorConfig(
            window_days=30,
            recent_days=29,
            daily_days=1,
            topics=["ai"],
            topic_keywords={"ai": ["test"]},
        )
        assert config.recent_days < config.window_days

        # daily_days = recent_days (有效)
        config = DetectorConfig(
            window_days=30,
            recent_days=7,
            daily_days=7,
            topics=["ai"],
            topic_keywords={"ai": ["test"]},
        )
        assert config.daily_days == config.recent_days


class TestLoadConfig:
    """load_config 函数测试"""

    def test_load_config_nonexistent_file(self) -> None:
        """测试加载不存在的配置文件"""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("config/nonexistent_config.yml")
        error_msg = str(exc_info.value)
        assert "配置文件不存在" in error_msg
