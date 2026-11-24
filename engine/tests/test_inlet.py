"""入口层单测：方言解析顺序（registry → engine → unsupported）、字段映射、适配器、WKB。"""
from __future__ import annotations

import csv
import gzip
import json
import os
import struct
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine import inlet  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    return inlet.load_registry()


@pytest.fixture(scope="module")
def eng():
    return inlet.load_engine_dialects()


def test_registry_dialects_loaded_and_frozen(reg):
    assert {"agol-t110101-buildingpoint", "agol-t110111-buildingpoint", "agol-t110000-buildingpoint"} <= set(reg)
    assert all(d["origin"] == "registry" for d in reg.values())
    assert reg["agol-t110101-buildingpoint"]["fields"]["number"]       # 别名表来自 registry


def test_engine_dialects_cover_five_source_families(eng):
    fams = {d["family"] for d in eng.values()}
    assert {"nad", "oa", "tiger", "granit", "overture"} <= fams


def test_resolve_prefers_registry_then_engine(reg, eng):
    assert inlet.resolve_dialect("agol-t110101-buildingpoint", reg, eng)["origin"] == "registry"
    assert inlet.resolve_dialect("nad-v1", reg, eng)["origin"] == "engine"


def test_unknown_dialect_raises_unsupported(reg, eng):
    with pytest.raises(inlet.Unsupported) as e:
        inlet.resolve_dialect("no-such-dialect", reg, eng)
    assert "dialect_not_defined" in str(e.value)


def test_probe_sources_reports_unsupported_without_guessing(reg, eng):
    srcs = [{"id": "good", "family": "nad", "dialect": "nad-v1", "path": "x.ndjson"},
            {"id": "bad_dialect", "family": "x", "dialect": "nope-v9", "path": "y"},
            {"id": "bad_adapter", "family": "x", "dialect": "nad-v1", "adapter": "soap", "path": "z"}]
    ok, bad = inlet.probe_sources(srcs, reg, eng)
    assert [s["id"] for s, _ in ok] == ["good"]
    assert {b["source_id"] for b in bad} == {"bad_dialect", "bad_adapter"}
    assert any("dialect_not_defined" in b["reason"] for b in bad)
    assert any("adapter_not_implemented" in b["reason"] for b in bad)


def test_map_row_uses_dialect_aliases(eng):
    spec = eng["nad-v1"]
    out = inlet.map_row({"Add_Number": "425", "StNam_Full": "LITTLE EDEN Way", "St_PosTyp": "Way",
                         "State": "DE", "Zip_Code": "19904", "Longitude": "-75.5", "Latitude": "39.1"},
                        spec, {"id": "s", "family": "nad"})
    assert out["number"] == "425" and out["street"] == "LITTLE EDEN Way"
    assert out["zip"] == "19904" and out["lon"] == "-75.5"


def test_ndjson_adapter_reads_gzip(tmp_path, eng):
    p = tmp_path / "a.ndjson.gz"
    with gzip.open(p, "wt") as fh:
        fh.write(json.dumps({"Add_Number": "1", "St_Name": "Main", "State": "NH"}) + "\n")
        fh.write("\n")                                    # 空行要跳过
    rows = list(inlet.iterate({"id": "t", "family": "nad", "path": str(p)}, eng["nad-v1"]))
    assert len(rows) == 1 and rows[0]["number"] == "1"


def test_zip_csv_adapter_reads_openaddresses(tmp_path, eng):
    p = tmp_path / "oa.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("us/nh/x.csv", "LON,LAT,NUMBER,STREET,CITY,REGION,POSTCODE\n-71.3,43.4,58,Barbara Dr,Alton,NH,03249\n")
    rows = list(inlet.iterate({"id": "t", "family": "oa", "path": str(p)}, eng["oa-v1"]))
    assert len(rows) == 1 and rows[0]["street"] == "Barbara Dr" and rows[0]["state"] == "NH"


def test_samples_csv_adapter_reads_addr_fields(tmp_path, eng):
    p = tmp_path / "DE.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["layer_url", "layer_id", "state", "provider", "addr_fields_json", "lon", "lat",
                    "lon_raw", "lat_raw", "wkid", "geom_type", "row_index", "sample_source"])
        w.writerow(["https://x/0", "L0", "DE", "p", json.dumps({"HOUSE_NUM": "5", "STREET": "Main St"}),
                    "-75.5", "39.1", "-75.5", "39.1", "4326", "esriGeometryPoint", 0, "arcgis_query"])
    rows = list(inlet.iterate({"id": "t", "family": "dialect_layer", "path": str(p)},
                              eng["engine-dialect-samples-v1"]))
    assert rows[0]["lon"] == "-75.5" and rows[0]["source_ref_url"] == "https://x/0"


def test_parquet_adapter_reads_wkb_point(tmp_path, eng):
    import pyarrow as pa
    import pyarrow.parquet as pq
    wkb = b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", -75.5, 39.1)
    tbl = pa.table({"id": ["a"], "street": ["Main"], "number": ["1"], "unit": [None],
                    "postcode": ["19901"], "postal_city": ["Dover"], "geometry": [wkb],
                    "address_levels": [[{"value": "DE"}]]})
    p = tmp_path / "o.parquet"
    pq.write_table(tbl, p)
    rows = list(inlet.iterate({"id": "t", "family": "overture", "path": str(p)}, eng["overture-v1"]))
    assert rows[0]["state"] == "DE" and abs(float(rows[0]["lon"]) + 75.5) < 1e-9


def test_wkb_point_rejects_non_point():
    line = b"\x01" + struct.pack("<I", 2) + struct.pack("<dd", 1.0, 2.0)
    assert inlet.wkb_point(line) == (None, None)
    assert inlet.wkb_point(b"") == (None, None)
