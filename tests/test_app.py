from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
VALID_CSV = b"shear_rate,viscosity\n1,12\n4,6\n9,4\n16,3\n36,2\n"
CONSTANT_CSV = b"shear_rate,viscosity\n1,2.5\n2,2.5\n3,2.5\n4,2.5\n5,2.5\n"


@pytest.fixture
def app():
    application = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
    assert not application.exception
    return application


def upload(app, content=VALID_CSV, name="measurements.csv"):
    return (
        app.file_uploader(key="csv_file").set_value((name, content, "text/csv")).run()
    )


def assert_no_results(app):
    assert not app.exception
    assert not app.metric
    assert not app.get("plotly_chart")


def test_initial_page_waits_for_input(app):
    assert app.title[0].value == "RheoLab"
    assert app.file_uploader
    assert not app.dataframe
    assert_no_results(app)


def test_uploaded_csv_preview_and_fit(app):
    upload(app)
    assert len(app.dataframe[0].value) == 5
    assert_no_results(app)
    app.button(key="fit").click().run()
    assert not app.exception
    values = {metric.label: metric.value for metric in app.metric}
    assert float(values["K (Pa·sⁿ)"]) == pytest.approx(12)
    assert float(values["n"]) == pytest.approx(0.5)
    assert float(values["R²（对数空间）"]) == pytest.approx(1)
    assert float(values["RMSE (Pa·s)"]) < 1e-10
    assert float(values["MAPE"].removesuffix("%")) < 1e-10
    assert len(app.get("plotly_chart")) == 1


def test_demo_can_be_fitted_and_is_marked_synthetic(app):
    app.radio(key="data_source").set_value("合成示例（非实验数据）").run()
    assert len(app.dataframe[0].value) == 80
    assert any("合成数据" in message.value for message in app.info)
    assert_no_results(app)
    app.button(key="fit").click().run()
    assert not app.exception
    assert len(app.metric) == 5
    assert len(app.get("plotly_chart")) == 1


@pytest.mark.parametrize("name", ["measurements.csv", "different.csv"])
def test_replacing_file_clears_previous_result_even_with_same_name(app, name):
    upload(app)
    app.button(key="fit").click().run()
    assert app.metric
    upload(app, CONSTANT_CSV, name)
    assert len(app.dataframe[0].value) == 5
    assert_no_results(app)
    app.button(key="fit").click().run()
    assert app.metric[0].value == "2.5"
    assert app.metric[2].value == "未定义"


def test_removing_file_clears_previous_result(app):
    upload(app)
    app.button(key="fit").click().run()
    assert app.metric
    app.file_uploader(key="csv_file").set_value(None).run()
    assert not app.dataframe
    assert_no_results(app)


def test_changing_source_clears_previous_result(app):
    upload(app)
    app.button(key="fit").click().run()
    assert app.metric
    app.radio(key="data_source").set_value("合成示例（非实验数据）").run()
    assert_no_results(app)
    app.button(key="fit").click().run()
    assert app.metric
    app.radio(key="data_source").set_value("上传 CSV").run()
    assert_no_results(app)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"rate,viscosity\n1,2", "shear_rate"),
        (b"shear_rate,viscosity\n1,2\n2,2\n3,2\n4,2\n4,2", "5 distinct"),
        (VALID_CSV.replace(b"4,6", b"4,0"), "viscosity data row 2"),
        (b"", "empty"),
    ],
)
def test_invalid_replacement_shows_error_and_hides_old_result(app, content, message):
    upload(app)
    app.button(key="fit").click().run()
    assert app.metric
    upload(app, content)
    assert message in app.error[0].value
    assert "数据校验失败" in app.error[0].value
    assert not app.dataframe
    assert_no_results(app)


def test_fit_failure_does_not_leave_previous_success(app, monkeypatch):
    upload(app)
    app.button(key="fit").click().run()
    assert app.metric

    def fail(*args, **kwargs):
        raise ValueError("controlled fit failure")

    monkeypatch.setattr("rheolab.fitting.fit_power_law", fail)
    app.button(key="fit").click().run()
    assert "拟合失败" in app.error[0].value
    assert "controlled fit failure" in app.error[0].value
    assert_no_results(app)


def test_plotting_failure_hides_success_metrics(app, monkeypatch):
    upload(app)

    def fail(*args, **kwargs):
        raise ValueError("controlled plotting failure")

    monkeypatch.setattr("rheolab.plotting.create_fit_figure", fail)
    app.button(key="fit").click().run()
    assert "结果绘图失败" in app.error[0].value
    assert_no_results(app)
