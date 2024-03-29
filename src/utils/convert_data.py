# Functions to manipulate data sets
import geopandas as gpd
import pandas as pd
import json
import os
import re
from dotenv import load_dotenv

# Set global variables and read boundary files
load_dotenv("src/.env")
PROJECT_CRS = os.getenv("PROJECT_CRS")

v_boundary_gdf = gpd.read_file(
    "src/data/EGMS_L3_100km_U_2018_2022_BOUNDARY.geojson"
).to_crs(PROJECT_CRS)
h_boundary_gdf = gpd.read_file(
    "src/data/EGMS_L3_100km_E_2018_2022_BOUNDARY.geojson"
).to_crs(PROJECT_CRS)


def convert_geojson_to_geodataframe(
        geojson,
        input_crs: str="EPSG: 4326") -> gpd.GeoDataFrame:
    """Convert a GeoJSON object to a GeoPandas
    GeoDataframe

    Parameters
    ----------
    geojson : a GeoJSON object with 'features' geometry
    input_crs : a string denoting the CRS of the GeoJSON shape

    Returns
    ----------
    GeoPandas GeoDataFrame
    """
    return (gpd.GeoDataFrame
            .from_features(geojson["features"])
            .set_crs(crs=input_crs))


def convert_json_to_geodataframe(json_dict) -> gpd.GeoDataFrame:
    """Convert JSON dict to GeoPandas GeoDataframe

    Parameters
    ----------
    json_dict : a JSON dict object with 'features' key

    Returns
    ----------
    GeoPandas GeoDataFrame
    """
    data = json.loads(json_dict)
    return (gpd.GeoDataFrame
            .from_features(data["features"])
            .set_crs(crs=PROJECT_CRS))


def intersect_gdf(gdf1: gpd.GeoDataFrame,
                  gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect 2 GeoDataFrames

    Parameters
    ----------
    gdf1 : pandas GeoDataFrame which is used as the left
        GeoDataFrame to join on
    gdf2 : pandas GeoDataFrame which is used as the right
        GeoDataFrame to join on

    Returns
    ----------
    Intersected GeoPandas GeoDataFrame without an index
        in the column values
    """
    # Check CRS match project CRS and intersect
    if gdf1.crs != PROJECT_CRS:
        gdf1 = gdf1.to_crs(PROJECT_CRS)
    if gdf2.crs != PROJECT_CRS:
        gdf2 = gdf2.to_crs(PROJECT_CRS)
    intersect_gdf = gdf1.sjoin(gdf2, predicate="intersects")

    # Remove any index columns from joined GeoDataFrame
    return (intersect_gdf
            .drop(intersect_gdf
                  .filter(regex='index')
                  .columns, axis=1)
            )


def points_in_polygon(points_gdf: gpd.GeoDataFrame,
                      poly_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect 2 GeoDataFrames

    Parameters
    ----------
    gdf1 : points GeoDataFrame
    gdf2 : pandas GeoDataFrame which is used as the right
        GeoDataFrame to join on

    Returns
    ----------
    Intersected GeoPandas GeoDataFrame without an index
        in the column values
    """
    # Check CRS match project CRS and intersect
    if points_gdf.crs != PROJECT_CRS:
        points_gdf = points_gdf.to_crs(PROJECT_CRS)
    if poly_gdf.crs != PROJECT_CRS:
        poly_gdf = poly_gdf.to_crs(PROJECT_CRS)
    within_gdf = gpd.sjoin(points_gdf, poly_gdf, how="inner", predicate="within")

    # Remove any index columns from joined GeoDataFrame
    return (within_gdf
            .drop(within_gdf
                  .filter(regex='index')
                  .columns, axis=1)
            )


def get_boundary_data(product: str="ortho", direction: str="vertical"):
    """Return data for different EGMS products

    Parameters
    ----------
    product : EGMS product - one of ortho, calibrated, basic
    direction : dependent on EGMS product, vertical/ascending etc
    """
    if direction == "vertical":
        return v_boundary_gdf
    elif direction == "horizontal":
        return h_boundary_gdf


def get_point_data(click_data):
    data = pd.read_json(json.dumps(click_data))
    return data.loc["pid", "properties"]


def get_pid_from_pointclick(json_data):
    gdf = convert_json_to_geodataframe(json_data)
    return gdf["pid"].values


def get_timeseries_from_pid(df: pd.DataFrame, pid: str) -> pd.DataFrame:
    """Return the time series from EGMS dataset
    from a specific pid

    Parameters
    ----------
    df : EGMS data in pandas DataFrame format
    pid : pid value for time series to be filtered

    Returns
    ----------
    DataFrame containing only time series measurements for specific pid
    """
    date_cols = get_date_cols(df)
    return df[df["pid"] == pid][date_cols]


def get_date_cols(df: pd.DataFrame, date_format: str=r"^\d{8}$"):
    """Return the date columns from a dataframe
    that match the date format pattern

    Parameters
    ----------
    df : pandas DataFrame with dates in columns
    date_format : specific format of the date in the dataframe

    Returns
    ----------
    ordered list of date columns
    """
    date_cols = [col for col in df.columns if re.match(date_format, col)]
    return sorted(date_cols)
