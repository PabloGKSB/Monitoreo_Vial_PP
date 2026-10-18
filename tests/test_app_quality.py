from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import loader, maps
from src.analyzer import TripAnalyzer
from test_analyzer import _trip_zip
from test_native_loader import native_archive
from test_processing_policy import make_trip


@pytest.mark.parametrize("native", [False,True])
def test_app_shows_not_evaluated_instead_of_zero(tmp_path,monkeypatch,native):
    path = native_archive(tmp_path) if native else tmp_path / "invalid.zip"
    if not native:
        _trip_zip(path)
        monkeypatch.setattr("src.analyzer.load_trip",lambda _:make_trip(invalid_gps=True))
    monkeypatch.setattr(loader,"discover_trip_archives",lambda *args:[path])
    original_export = TripAnalyzer.export
    original_map = maps.save_trip_map
    monkeypatch.setattr(TripAnalyzer,"export",lambda self,result,root:original_export(self,result,tmp_path / "outputs"))
    monkeypatch.setattr(maps,"save_trip_map",lambda result,destination:original_map(result,tmp_path / "map.html"))
    st.cache_resource.clear()
    app = AppTest.from_file(str(Path(__file__).parents[1]/"app.py"))
    app.run(timeout=30)
    app.selectbox[0].select(path.name).run(timeout=30)
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label=="Detecciones").value == "No evaluadas"
    if not native:
        assert any("deteccion bloqueada" in error.value.lower() for error in app.error)
    st.cache_resource.clear()
