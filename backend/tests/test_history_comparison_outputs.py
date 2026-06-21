import sys
import unittest
import inspect
import tempfile
import re
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.chart_service import _FONT_FAMILIES, _get_chart_font, _get_chart_font_family, _get_chart_font_path, generate_all_charts  # noqa: E402
from services import docx_service  # noqa: E402
from services.report_figures import (
    augment_text_with_figure_references,
    build_figure_manifest,
    order_manifest_for_text,
)  # noqa: E402
from services.report_service import ReportService, build_history_comparison_summary  # noqa: E402


class HistoryComparisonOutputTests(unittest.TestCase):
    def test_chart_fonts_prioritize_simplified_chinese_before_japanese_fallback(self):
        self.assertIn("WenQuanYi Zen Hei", _FONT_FAMILIES)
        self.assertIn("Noto Sans CJK SC", _FONT_FAMILIES)
        self.assertIn("Noto Sans CJK JP", _FONT_FAMILIES)
        self.assertLess(_FONT_FAMILIES.index("WenQuanYi Zen Hei"), _FONT_FAMILIES.index("Noto Sans CJK JP"))
        self.assertLess(_FONT_FAMILIES.index("Noto Sans CJK SC"), _FONT_FAMILIES.index("Noto Sans CJK JP"))

    def test_chart_font_resolves_to_specific_font_file(self):
        family = _get_chart_font_family()
        self.assertIsNotNone(family)
        self.assertIn(family, _FONT_FAMILIES)
        font_path = _get_chart_font_path()
        font = _get_chart_font()
        self.assertTrue(font.get_family())
        if font.get_file():
            self.assertTrue(Path(font.get_file()).exists())
        elif font_path is not None:
            self.assertTrue(Path(font_path).exists())
        bold_font = _get_chart_font(weight="bold")
        self.assertTrue(bold_font.get_family() or bold_font.get_file())

    def test_build_history_comparison_summary_returns_module_deltas(self):
        current_period = {"start": "2026-03-25", "end": "2026-04-23"}
        previous_period = {"start": "2026-02-23", "end": "2026-03-24"}
        current = {
            "insect": {"total_count": 73},
            "spore": {"total_count": 22},
            "rain": {"total_rainfall": 188.5},
            "runoff": {"total_runoff": 24.6},
            "water_quality": {
                "avg_nh3_n": 0.13,
                "avg_tp": 0.02,
                "avg_permanganate": 1.8,
                "avg_tn": 0.57,
            },
        }
        previous = {
            "insect": {"total_count": 58},
            "spore": {"total_count": 17},
            "rain": {"total_rainfall": 132.0},
            "runoff": {"total_runoff": 18.4},
            "water_quality": {
                "avg_nh3_n": 0.21,
                "avg_tp": 0.03,
                "avg_permanganate": 2.1,
                "avg_tn": 0.63,
            },
        }

        history = build_history_comparison_summary(
            current_period=current_period,
            previous_period=previous_period,
            current=current,
            previous=previous,
        )

        self.assertEqual(previous_period, history["previous_period"])
        self.assertEqual(25.9, history["modules"]["insect"]["change_rate"])
        self.assertEqual("上升", history["modules"]["rain"]["trend"])
        self.assertEqual("下降", history["water_quality"]["metrics"][0]["trend"])

    def test_generate_all_charts_and_manifest_include_history_comparison_figures(self):
        summary = {
            "insect": {"daily": [{"date": "2026-04-01", "count": 12}], "top_species": [["金龟子", 32]]},
            "spore": {"daily": [{"date": "2026-04-01", "count": 3}]},
            "rain": {"daily": [{"date": "2026-04-01", "rainfall": 18.5}], "total_rainfall": 188.5},
            "runoff": {
                "by_device": {
                    "16132922": {"name": "次生林监测点", "total_runoff": 24.6},
                    "16132921": {"name": "橡胶林监测点", "total_runoff": 12.2},
                }
            },
            "water_quality": {
                "avg_nh3_n": 0.13,
                "avg_tp": 0.02,
                "avg_permanganate": 1.8,
                "avg_tn": 0.57,
            },
            "history_comparison": {
                "modules": {
                    "insect": {"label": "虫情测报", "unit": "%", "change_rate": 25.9},
                    "spore": {"label": "孢子监测", "unit": "%", "change_rate": 29.4},
                    "rain": {"label": "雨量监测", "unit": "%", "change_rate": 42.8},
                    "runoff": {"label": "地表径流监测", "unit": "%", "change_rate": 33.7},
                },
                "water_quality": {
                    "metrics": [
                        {"label": "氨氮", "current_value": 0.13, "previous_value": 0.21},
                        {"label": "总磷", "current_value": 0.02, "previous_value": 0.03},
                        {"label": "高锰酸盐指数", "current_value": 1.8, "previous_value": 2.1},
                        {"label": "总氮", "current_value": 0.57, "previous_value": 0.63},
                    ]
                },
            },
        }

        charts = generate_all_charts(summary)

        self.assertTrue(charts["核心指标历史对比"])
        self.assertTrue(charts["水质历史对比"])

        manifest = build_figure_manifest(summary, charts, {})
        captions = [item["caption"] for item in manifest]
        self.assertIn("本期与上一等长周期核心监测指标变化率", captions)
        self.assertIn("水质关键指标本期与上一周期均值对比", captions)

    def test_html_report_includes_warning_rules_and_real_history_comparison(self):
        summary = {
            "period": {"start": "2026-04-01", "end": "2026-04-30"},
            "insect": {"records_count": 3, "total_count": 90, "daily": [{"date": "2026-04-10", "count": 90}], "top_species": [["甜菜夜蛾", 90]]},
            "spore": {"capture_images": []},
            "rain": {"records_count": 2, "total_rainfall": 88.0, "daily": [{"date": "2026-04-12", "rainfall": 44.0}]},
            "runoff": {"records_count": 2, "device_count": 1, "total_runoff": 18.0, "by_device": {"16132922": {"name": "次生林监测点", "total_runoff": 18.0, "avg_sand_content": 0.0012}}},
            "water_quality": {"records_count": 2, "avg_nh3_n": 0.2, "avg_tp": 0.03, "avg_permanganate": 1.8, "avg_tn": 0.6},
            "history_comparison": build_history_comparison_summary(
                current_period={"start": "2026-04-01", "end": "2026-04-30"},
                previous_period={"start": "2026-03-02", "end": "2026-03-31"},
                current={
                    "insect": {"total_count": 90},
                    "spore": {"total_count": 0},
                    "rain": {"total_rainfall": 88.0},
                    "runoff": {"total_runoff": 18.0},
                    "water_quality": {"avg_nh3_n": 0.2, "avg_tp": 0.03, "avg_permanganate": 1.8, "avg_tn": 0.6},
                },
                previous={
                    "insect": {"total_count": 45},
                    "spore": {"total_count": 0},
                    "rain": {"total_rainfall": 44.0},
                    "runoff": {"total_runoff": 12.0},
                    "water_quality": {"avg_nh3_n": 0.24, "avg_tp": 0.04, "avg_permanganate": 2.0, "avg_tn": 0.7},
                },
            ),
            "guideline_metrics": {
                "runoff_erosion": {
                    "estimated_reduction_rate": 12.5,
                    "station_metrics": [],
                    "highest_risk_station": {"name": "次生林监测点", "avg_sand_content": 0.0012},
                },
                "water_quality": {"composite_reduction_rate": 18.2, "metrics": []},
                "pest_management": {"risk_level": "中", "insect_peak": {"date": "2026-04-10", "count": 90}, "top_species": {"name": "甜菜夜蛾"}},
                "warning_analysis": {
                    "comparison": {
                        "available": True,
                        "message": "历史同口径对比已接入：虫情测报上升100.0%，雨量监测上升100.0%，地表径流监测上升50.0%。",
                    },
                    "indicator_warnings": [
                        {
                            "key": "insect_peak",
                            "title": "虫情单日峰值",
                            "metric_label": "最近30天单日虫情峰值",
                            "basis": "按最近30天日累计虫情进行分级判定",
                            "level": "较严重",
                            "level_code": "severe",
                            "score": 55,
                            "display_value": "90 只",
                            "band": "80 - 100 只",
                            "rule_text": "关注 40 - 80 只；较严重 80 - 100 只；高等级 100 - 120 只；极高 >= 120 只",
                            "summary": "虫情峰值达到90只。",
                            "action": "建议同步开展田间复核。",
                        }
                    ],
                },
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})

        self.assertIn("历史同口径对比已接入", html)
        self.assertNotIn("历史数据暂缺", html)
        self.assertIn("判定依据：按最近30天日累计虫情进行分级判定", html)
        self.assertIn("判定标准：关注 40 - 80 只", html)

    def test_report_special_analysis_is_section_eight_and_data_chart_appendix_removed(self):
        summary = {
            "period": {"start": "2026-04-01", "end": "2026-04-30"},
            "insect": {"records_count": 1, "total_count": 1, "daily": [{"date": "2026-04-01", "count": 1}], "top_species": [["甜菜夜蛾", 1]]},
            "spore": {"capture_images": []},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": build_history_comparison_summary(
                current_period={"start": "2026-04-01", "end": "2026-04-30"},
                previous_period={"start": "2026-03-02", "end": "2026-03-31"},
                current={"insect": {"total_count": 1}, "spore": {}, "rain": {}, "runoff": {}, "water_quality": {}},
                previous={"insect": {"total_count": 0}, "spore": {}, "rain": {}, "runoff": {}, "water_quality": {}},
            ),
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {},
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})
        docx_source = inspect.getsource(docx_service.generate_docx_report)
        special_source = inspect.getsource(docx_service._append_special_analysis_section)

        self.assertIn('<span class="toc-num">五、</span>四类深度专项分析', html)
        self.assertIn('<span class="sec-num">五</span>四类深度专项分析', html)
        self.assertIn('"八、四类深度专项分析"', special_source)
        self.assertNotIn("附录：数据图表", docx_source)

    def test_html_report_top_level_section_numbers_are_sequential(self):
        summary = {
            "period": {"start": "2026-04-01", "end": "2026-04-30"},
            "insect": {"records_count": 0, "total_count": 0, "daily": [], "top_species": [], "capture_images": []},
            "spore": {"capture_images": []},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": {},
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {},
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})

        toc_numbers = re.findall(r'<span class="toc-num">([^<]+)</span>', html)
        section_numbers = re.findall(r'<span class="sec-num">([^<]+)</span>', html)
        self.assertEqual(["一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、"], toc_numbers)
        self.assertEqual(["一", "二", "三", "四", "五", "六", "七", "八"], section_numbers)

    def test_html_report_includes_insect_capture_image_appendix(self):
        images = [
            {
                "time": f"2026-05-0{idx} 08:00",
                "device_code": "insect-1",
                "url": f"https://example.com/insect-{idx}.jpg",
            }
            for idx in range(1, 4)
        ]
        summary = {
            "period": {"start": "2026-05-01", "end": "2026-05-07"},
            "insect": {"records_count": 3, "total_count": 9, "daily": [], "top_species": [], "capture_images": images},
            "spore": {"capture_images": []},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": {},
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {},
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})

        self.assertIn('<span class="toc-num">七、</span>虫情采集图像附录', html)
        self.assertIn('<span class="sec-num">七</span>虫情采集图像附录', html)
        self.assertEqual(3, html.count('id="fig-insect-appendix-'))
        self.assertIn("https://example.com/insect-1.jpg", html)
        self.assertIn("https://example.com/insect-3.jpg", html)

    def test_report_body_adds_missing_figure_references_by_section(self):
        manifest = [
            {"number": 1, "section": "hydrology", "caption": "监测期每日降雨量"},
            {"number": 2, "section": "hydrology", "caption": "各监测点累计径流量对比"},
            {"number": 3, "section": "water_quality", "caption": "水质关键指标平均值"},
            {"number": 4, "section": "insect", "caption": "每日虫情捕获量"},
        ]
        text = "\n".join(
            [
                "## 二、森林生物多样性与生态健康指标分析",
                "虫情监测形成有效记录。",
                "## 三、水文调节功能与水土流失监测分析",
                "降雨与径流指标用于分析水土保持效果。",
                "## 四、区域水环境质量与生态容量评价",
                "水质指标用于判断面源污染负荷。",
            ]
        )

        manifest = order_manifest_for_text(manifest, text)
        augmented = augment_text_with_figure_references(text, manifest)

        self.assertIn("本章相关图表见图1。", augmented)
        self.assertIn("本章相关图表见图2、图3。", augmented)
        self.assertIn("本章相关图表见图4。", augmented)
        self.assertLess(augmented.index("图1"), augmented.index("图2"))
        self.assertLess(augmented.index("图2"), augmented.index("图4"))

    def test_docx_inserts_only_explicitly_referenced_figures(self):
        source = inspect.getsource(docx_service.generate_docx_report)

        self.assertIn("_insert_referenced_figures(refs)", source)
        self.assertNotIn("_insert_figures_through(max(refs))", source)

    def test_docx_figure_insertion_follows_body_reference_positions(self):
        manifest = [
            {"number": 1, "section": "hydrology", "caption": "监测期每日降雨量", "src": "data:image/png;base64,AA=="},
            {"number": 2, "section": "hydrology", "caption": "各监测点累计径流量对比", "src": "data:image/png;base64,AA=="},
            {"number": 3, "section": "water_quality", "caption": "水质关键指标平均值", "src": "data:image/png;base64,AA=="},
            {"number": 4, "section": "insect", "caption": "每日虫情捕获量", "src": "data:image/png;base64,AA=="},
        ]
        ai_analysis = "\n".join(
            [
                "## 二、森林生物多样性与生态健康指标分析",
                "虫情监测形成有效记录。",
                "## 三、水文调节功能与水土流失监测分析",
                "降雨与径流指标用于分析水土保持效果。",
                "## 四、区域水环境质量与生态容量评价",
                "水质指标用于判断面源污染负荷。",
            ]
        )
        manifest = order_manifest_for_text(manifest, ai_analysis)
        inserted: list[int] = []
        original_insert_figure = docx_service._insert_figure
        original_append_device_images = docx_service._append_device_image_section
        original_refresh_fields = docx_service._refresh_word_fields

        def fake_insert_figure(_doc, _image_src, caption, width_inches=5.5):
            inserted.append(int(caption.split()[0].replace("图", "")))

        try:
            docx_service._insert_figure = fake_insert_figure
            docx_service._append_device_image_section = lambda _doc, _summary: None
            docx_service._refresh_word_fields = lambda _filepath: None
            with tempfile.TemporaryDirectory() as tmpdir:
                filepath = str(Path(tmpdir) / "report.docx")
                docx_service.generate_docx_report(
                    {"period": {}, "guideline_metrics": {}},
                    ai_analysis,
                    {},
                    {},
                    filepath,
                    figure_manifest=manifest,
                )
        finally:
            docx_service._insert_figure = original_insert_figure
            docx_service._append_device_image_section = original_append_device_images
            docx_service._refresh_word_fields = original_refresh_fields

        self.assertEqual([1, 2, 3, 4], inserted)

    def test_html_report_renumbers_figures_in_body_order(self):
        summary = {
            "period": {},
            "insect": {
                "records_count": 1,
                "total_count": 1,
                "daily": [],
                "top_species": [],
                "capture_images": [],
            },
            "spore": {"capture_images": []},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": {},
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {},
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }
        charts = {
            "雨量日统计": "AA==",
            "虫情日捕获": "AA==",
            "虫种统计": "AA==",
        }
        ai_analysis = "\n".join(
            [
                "## 二、森林生物多样性与生态健康指标分析",
                "虫情监测形成有效记录（见图3）。",
                "## 三、水文调节功能与水土流失监测分析",
                "降雨与径流指标用于分析水土保持效果（见图2）。",
            ]
        )

        html = ReportService.generate_html_report(summary, ai_analysis=ai_analysis, charts=charts, ai_images={})

        self.assertIn("本章相关图表见图1、图2。", html)
        self.assertIn("本章相关图表见图3。", html)
        self.assertNotIn("虫情监测形成有效记录（见图3）", html)
        self.assertNotIn("降雨与径流指标用于分析水土保持效果（见图2）", html)
        self.assertLess(html.index("图1&nbsp;&nbsp;每日虫情捕获量"), html.index("图2&nbsp;&nbsp;主要虫种捕获量对比"))
        self.assertLess(html.index("图2&nbsp;&nbsp;主要虫种捕获量对比"), html.index("图3&nbsp;&nbsp;监测期每日降雨量"))
        captions = [
            int(match.group(1))
            for match in re.finditer(r"<figcaption>图(\d+)&nbsp;&nbsp;", html)
        ]
        self.assertEqual(list(range(1, len(captions) + 1)), captions)

    def test_html_report_includes_all_spore_images_in_period(self):
        images = [
            {
                "time": f"2026-05-{day:02d} 08:00",
                "device_code": "spore-1",
                "url": f"https://example.com/spore-{day}.jpg",
            }
            for day in range(1, 16)
        ]
        summary = {
            "period": {"start": "2026-05-01", "end": "2026-05-15"},
            "insect": {"records_count": 0, "total_count": 0, "daily": [], "top_species": [], "capture_images": []},
            "spore": {"records_count": 15, "total_count": 15, "daily": [], "capture_images": images},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": {},
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {},
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})

        self.assertEqual(15, html.count('id="fig-spore-appendix-'))
        self.assertIn("https://example.com/spore-1.jpg", html)
        self.assertIn("https://example.com/spore-15.jpg", html)

    def test_html_report_keeps_only_spore_image_appendix(self):
        images = [
            {
                "time": "2026-05-01 08:00",
                "device_code": "spore-1",
                "url": "https://example.com/spore-1.jpg",
            }
        ]
        summary = {
            "period": {"start": "2026-05-01", "end": "2026-05-15"},
            "insect": {"records_count": 1, "total_count": 12, "daily": [{"date": "2026-05-01", "count": 12}], "top_species": [["甜菜夜蛾", 12]], "capture_images": []},
            "spore": {"records_count": 15, "total_count": 15, "daily": [{"date": "2026-05-01", "count": 15}], "capture_images": images},
            "rain": {"records_count": 0, "total_rainfall": 0, "daily": []},
            "runoff": {"records_count": 0, "device_count": 0, "total_runoff": 0, "by_device": {}},
            "water_quality": {"records_count": 0},
            "history_comparison": {
                "modules": {
                    "spore": {
                        "label": "孢子监测",
                        "metric_label": "周期内有效捕获孢子",
                        "current_value": 15,
                        "previous_value": 0,
                        "change_rate": None,
                        "trend": "上升",
                        "unit": "个",
                    }
                }
            },
            "guideline_metrics": {
                "runoff_erosion": {},
                "water_quality": {},
                "pest_management": {
                    "available": True,
                    "risk_level": "中",
                    "insect_peak": {"date": "2026-05-01", "count": 12},
                    "suggestion": "建议提高巡检频率，并持续跟踪孢子波动。",
                    "chain_text": "虫情峰值出现在2026-05-01；孢子峰值出现在2026-05-02。",
                },
                "warning_analysis": {"indicator_warnings": []},
                "water_source_support": {},
                "implementation_matrix": {},
                "methodology": {
                    "monitoring_statement": "本项目构建了覆盖径流、雨量、水质、虫情和孢子的在线监测网络。",
                    "baseline_statement": "统一按前30天建立基准。",
                },
            },
        }

        html = ReportService.generate_html_report(summary, ai_analysis="", charts={}, ai_images={})

        self.assertIn("孢子采集图像附录", html)
        self.assertIn("https://example.com/spore-1.jpg", html)
        self.assertNotIn("孢子监测", html)
        self.assertNotIn("周期内有效捕获孢子", html)
        self.assertNotIn("孢子波动", html)
        self.assertNotIn("孢子峰值", html)
        self.assertNotIn("虫情和孢子", html)


if __name__ == "__main__":
    unittest.main()
