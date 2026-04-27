import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai_report import ANALYSIS_PROMPT_TEMPLATE, format_summary_for_prompt  # noqa: E402


class AiReportPromptFormatTests(unittest.TestCase):
    def test_prompt_template_does_not_expose_internal_field_names(self):
        forbidden_tokens = (
            "records_count",
            "device_count",
            "avg_flow_rate",
            "avg_flow_speed",
            "max_flow_rate",
            "baseline_avg",
            "recent_avg",
            "recent_reduction_rate",
            "records_count > 0",
            "对于 records_count 大于 0 的模块",
        )

        for token in forbidden_tokens:
            self.assertNotIn(token, ANALYSIS_PROMPT_TEMPLATE)

        self.assertIn("监测记录数大于 0", ANALYSIS_PROMPT_TEMPLATE)
        self.assertIn("严禁在正文中出现任何原始数据库字段名", ANALYSIS_PROMPT_TEMPLATE)
        self.assertIn("上一等长周期", ANALYSIS_PROMPT_TEMPLATE)
        self.assertIn("历史对比分析", ANALYSIS_PROMPT_TEMPLATE)
        self.assertIn("面向项目汇报和管理决策场景", ANALYSIS_PROMPT_TEMPLATE)

    def test_prompt_summary_uses_reader_facing_labels(self):
        summary = {
            "period": {"start": "2026-03-25", "end": "2026-04-23"},
            "insect": {
                "records_count": 73,
                "total_count": 73,
                "top_species": [["金龟子", 32]],
                "capture_images": [{"url": "https://example.com/insect.jpg"}],
                "daily": [{"date": "2026-04-01", "count": 12}],
            },
            "spore": {
                "records_count": 22,
                "total_count": 22,
                "capture_images": [{"url": "https://example.com/spore.jpg"}],
                "daily": [{"date": "2026-04-01", "count": 3}],
            },
            "water_quality": {
                "records_count": 951,
                "avg_nh3_n": 0.13,
                "avg_tp": 0.02,
                "avg_permanganate": 1.8,
                "avg_tn": 0.57,
            },
            "runoff": {
                "records_count": 20650,
                "device_count": 6,
                "avg_flow_rate": 0.25,
                "max_flow_rate": 1.2,
                "avg_water_level": 0.18,
                "by_device": {
                    "16132922": {
                        "name": "次生林监测点",
                        "records_count": 3440,
                        "avg_flow_speed": 0.1,
                        "max_flow_speed": 0.3,
                        "avg_flow_rate": 0.2,
                        "max_flow_rate": 0.9,
                        "total_flow_latest": 12.5,
                        "avg_water_level": 0.12,
                        "max_water_level": 0.35,
                        "avg_sand_content": 0.01,
                        "avg_liquid_pressure": 0.0,
                        "total_runoff": 24.6,
                        "total_rainfall": 88.0,
                    }
                },
            },
            "rain": {
                "records_count": 10252,
                "total_rainfall": 188.5,
            },
            "weather_support": {},
            "guideline_metrics": {
                "water_quality": {
                    "available": True,
                    "baseline_period": {
                        "start": "2026-03-25",
                        "end": "2026-04-23",
                        "records_count": 951,
                    },
                    "composite_reduction_rate": 18.6,
                    "metrics": [
                        {
                            "label": "氨氮",
                            "unit": "mg/L",
                            "baseline_avg": 0.21,
                            "recent_avg": 0.13,
                            "recent_reduction_rate": 38.1,
                        }
                    ],
                }
            },
            "history_comparison": {
                "current_period": {"start": "2026-03-25", "end": "2026-04-23"},
                "previous_period": {"start": "2026-02-23", "end": "2026-03-24"},
                "modules": {
                    "insect": {
                        "label": "虫情测报",
                        "metric_label": "周期内有效捕获昆虫",
                        "unit": "只",
                        "current_value": 73,
                        "previous_value": 58,
                        "change_value": 15,
                        "change_rate": 25.9,
                        "trend": "上升",
                    },
                    "rain": {
                        "label": "雨量监测",
                        "metric_label": "累计降雨量",
                        "unit": "mm",
                        "current_value": 188.5,
                        "previous_value": 132.0,
                        "change_value": 56.5,
                        "change_rate": 42.8,
                        "trend": "上升",
                    },
                },
                "water_quality": {
                    "metric_label": "水质关键指标周期均值对比",
                    "metrics": [
                        {
                            "label": "氨氮",
                            "unit": "mg/L",
                            "current_value": 0.13,
                            "previous_value": 0.21,
                            "change_value": -0.08,
                            "change_rate": -38.1,
                            "trend": "下降",
                        }
                    ],
                },
            },
        }

        prompt_summary = format_summary_for_prompt(summary)

        forbidden_tokens = (
            "records_count",
            "device_count",
            "avg_flow_rate",
            "avg_flow_speed",
            "max_flow_rate",
            "baseline_avg",
            "recent_avg",
            "recent_reduction_rate",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, prompt_summary)

        expected_labels = (
            "监测记录数",
            "监测点数量",
            "平均流量",
            "平均流速",
            "基准期记录数",
            "历史对比分析",
            "上一等长周期",
            "变化率",
        )
        for label in expected_labels:
            self.assertIn(label, prompt_summary)


if __name__ == "__main__":
    unittest.main()
