from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLEAU_DIR = PROJECT_ROOT / "tableau"
WORKBOOK_NAME = "retail_analytics_dashboard"
TWB_PATH = TABLEAU_DIR / f"{WORKBOOK_NAME}.twb"
TWBX_PATH = TABLEAU_DIR / f"{WORKBOOK_NAME}.twbx"


CSV_FILES = [
    "rfm_segments.csv",
    "promotion_roi.csv",
    "basket_affinity.csv",
    "targeting_recommendation.csv",
    "coupon_dependency.csv",
    "coupon_household_scores.csv",
]


def _column_xml(name: str, dtype: str) -> str:
    datatype = "real" if dtype in {"float64", "int64", "int32", "float32"} else "string"
    role = "measure" if datatype == "real" else "dimension"
    col_type = "quantitative" if datatype == "real" else "nominal"
    return (
        f'<column caption="{escape(name)}" datatype="{datatype}" '
        f'name="[{escape(name)}]" role="{role}" type="{col_type}" />'
    )


def _datasource_xml(name: str, csv_file: str) -> str:
    df = pd.read_csv(TABLEAU_DIR / csv_file, nrows=20)
    columns = "\n      ".join(_column_xml(col, str(dtype)) for col, dtype in df.dtypes.items())
    return f"""
  <datasource caption="{name}" inline="true" name="{name}" version="18.1">
    <connection class="textscan" directory="Data" filename="{csv_file}" header="yes" separator=",">
      <relation name="{csv_file}" table="[{csv_file.replace('.', '#')}]" type="table" />
    </connection>
    {columns}
  </datasource>"""


def _worksheet_xml(
    name: str,
    datasource: str,
    rows: str,
    cols: str,
    mark_class: str = "Bar",
) -> str:
    return f"""
  <worksheet name="{escape(name)}">
    <table>
      <view>
        <datasources>
          <datasource caption="{escape(datasource)}" name="{escape(datasource)}" />
        </datasources>
        <aggregation value="true" />
      </view>
      <style />
      <panes>
        <pane>
          <mark class="{mark_class}" />
        </pane>
      </panes>
      <rows>{rows}</rows>
      <cols>{cols}</cols>
    </table>
  </worksheet>"""


def _build_twb_xml() -> str:
    datasources = "\n".join(
        [
            _datasource_xml("rfm_segments", "rfm_segments.csv"),
            _datasource_xml("promotion_roi", "promotion_roi.csv"),
            _datasource_xml("basket_affinity", "basket_affinity.csv"),
            _datasource_xml("targeting_recommendation", "targeting_recommendation.csv"),
            _datasource_xml("coupon_dependency", "coupon_dependency.csv"),
            _datasource_xml("coupon_household_scores", "coupon_household_scores.csv"),
        ]
    )
    worksheets = "\n".join(
        [
            _worksheet_xml(
                "RFM Segment Distribution",
                "rfm_segments",
                "[rfm_segments].[segment]",
                "SUM([rfm_segments].[households])",
            ),
            _worksheet_xml(
                "Promotion ROI Ranking",
                "promotion_roi",
                "[promotion_roi].[campaign]",
                "SUM([promotion_roi].[incremental_revenue])",
            ),
            _worksheet_xml(
                "Basket Affinity Lift",
                "basket_affinity",
                "[basket_affinity].[category_affinity]",
                "SUM([basket_affinity].[lift])",
            ),
            _worksheet_xml(
                "Targeting Recommendation Revenue",
                "targeting_recommendation",
                "[targeting_recommendation].[segment]",
                "SUM([targeting_recommendation].[estimated_incremental_revenue])",
            ),
            _worksheet_xml(
                "Coupon Strategy Mix",
                "coupon_dependency",
                "[coupon_dependency].[segment]",
                "SUM([coupon_dependency].[coupon_households])",
            ),
        ]
    )
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-platform="mac" version="18.1">
  <preferences>
    <preference name="ui.encoding.shelf.height" value="24" />
    <preference name="ui.shelf.height" value="26" />
  </preferences>
  <datasources>
{datasources}
  </datasources>
  <worksheets>
{worksheets}
  </worksheets>
  <dashboards>
    <dashboard name="Retail Analytics Overview">
      <style />
      <size maxheight="1100" maxwidth="1200" minheight="1100" minwidth="1200" />
      <zones>
        <zone h="1100" id="1" type="layout-flow" w="1200" x="0" y="0">
          <zone h="450" id="2" name="RFM Segment Distribution" type="worksheet" w="600" x="0" y="0" />
          <zone h="450" id="3" name="Promotion ROI Ranking" type="worksheet" w="600" x="600" y="0" />
          <zone h="450" id="4" name="Basket Affinity Lift" type="worksheet" w="600" x="0" y="450" />
          <zone h="450" id="5" name="Targeting Recommendation Revenue" type="worksheet" w="600" x="600" y="450" />
          <zone h="200" id="6" name="Coupon Strategy Mix" type="worksheet" w="1200" x="0" y="900" />
        </zone>
      </zones>
    </dashboard>
  </dashboards>
</workbook>
"""


def build_workbook() -> Path:
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    missing = [csv for csv in CSV_FILES if not (TABLEAU_DIR / csv).exists()]
    if missing:
        raise FileNotFoundError(f"Missing Tableau CSV files: {', '.join(missing)}")

    TWB_PATH.write_text(_build_twb_xml(), encoding="utf-8")

    package_root = TABLEAU_DIR / "_twbx_package"
    data_dir = package_root / "Data"
    if package_root.exists():
        shutil.rmtree(package_root)
    data_dir.mkdir(parents=True)

    shutil.copy2(TWB_PATH, package_root / TWB_PATH.name)
    for csv_file in CSV_FILES:
        shutil.copy2(TABLEAU_DIR / csv_file, data_dir / csv_file)

    if TWBX_PATH.exists():
        TWBX_PATH.unlink()
    with zipfile.ZipFile(TWBX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(package_root / TWB_PATH.name, arcname=TWB_PATH.name)
        for csv_file in CSV_FILES:
            zf.write(data_dir / csv_file, arcname=f"Data/{csv_file}")

    shutil.rmtree(package_root)
    return TWBX_PATH


if __name__ == "__main__":
    output = build_workbook()
    print(f"Wrote Tableau packaged workbook to {output}")
